import os
import glob
import yaml

GITLAB_DIR = "../gitlab-templates"
GITHUB_DIR = "."
WORKFLOWS_DIR = os.path.join(GITHUB_DIR, ".github", "workflows")

os.makedirs(WORKFLOWS_DIR, exist_ok=True)

# Helper function to map variables
def map_variables(gitlab_vars):
    if not gitlab_vars:
        return {}
    github_vars = {}
    for k, v in gitlab_vars.items():
        github_vars[k] = str(v) # ensure it's a string
    return github_vars

def clean_script_steps(script_list):
    if not script_list:
        return ""
    # join multiple script lines into one string for 'run'
    if isinstance(script_list, list):
        return "\n".join(str(s) for s in script_list)
    return str(script_list)

def replace_gitlab_vars(text):
    if not text:
        return text
    replacements = {
        "$CI_PROJECT_DIR": "${{ github.workspace }}",
        "${CI_PROJECT_DIR}": "${{ github.workspace }}",
        "$CI_COMMIT_BRANCH": "${{ github.ref_name }}",
        "${CI_COMMIT_BRANCH}": "${{ github.ref_name }}",
        "$CI_COMMIT_TAG": "${{ github.ref_name }}",
        "${CI_COMMIT_TAG}": "${{ github.ref_name }}",
        "$CI_PIPELINE_SOURCE": "${{ github.event_name }}",
        "$CI_DEFAULT_BRANCH": "${{ github.event.repository.default_branch }}"
    }
    for gl_var, gh_var in replacements.items():
        text = text.replace(gl_var, gh_var)
    return text

def process_file(filepath):
    # Determine new filename based on folder structure
    rel_path = os.path.relpath(filepath, GITLAB_DIR)
    folder = os.path.dirname(rel_path)
    filename = os.path.basename(rel_path)
    
    if folder == "." or folder == "" or "graphify-out" in folder or ".venv" in folder or "scripts" in folder:
        return

    new_filename = f"{folder}-{filename}"
    new_filepath = os.path.join(WORKFLOWS_DIR, new_filename)

    with open(filepath, 'r') as f:
        try:
            yaml.SafeLoader.add_constructor('!reference', lambda loader, node: None)
            content = list(yaml.safe_load_all(f))
        except Exception as e:
            print(f"Skipping {filepath} due to parsing error: {e}")
            return
    
    if not content or not content[0]:
        return
        
    gitlab_data = content[0]
    
    if not isinstance(gitlab_data, dict):
        return

    # Initialize GitHub Actions skeleton
    github_action = {
        "name": new_filename.replace('.yml', '').replace('-', ' ').title(),
        "on": {
            "workflow_call": {
                "inputs": {},
                "secrets": {}
            }
        },
        "jobs": {}
    }

    global_vars = map_variables(gitlab_data.get('variables', {}))
    if global_vars:
        github_action['env'] = global_vars

    # Parse jobs
    for key, value in gitlab_data.items():
        if key in ['variables', 'stages', 'default', 'include', 'before_script', 'after_script'] or key.startswith('.'):
            continue
        
        if not isinstance(value, dict):
            continue
            
        job_id = key
        # job id cannot have spaces or special characters in GH, but usually gl ids are alphanumeric/dashes
        safe_job_id = job_id.replace(':', '-').replace(' ', '-')
        
        gh_job = {
            "runs-on": "ubuntu-latest",
            "steps": []
        }
        
        # Image -> Container
        image = value.get('image') or gitlab_data.get('image')
        if image:
            if isinstance(image, str):
                gh_job['container'] = {"image": image}
            elif isinstance(image, dict) and 'name' in image:
                gh_job['container'] = {"image": image['name']}
        
        # Services
        services = value.get('services', [])
        if services:
            gh_job['services'] = {}
            for idx, srv in enumerate(services):
                srv_name = srv if isinstance(srv, str) else srv.get('name', '')
                srv_alias = srv.get('alias', f"svc-{idx}") if isinstance(srv, dict) else srv_name.split(':')[0]
                if srv_name:
                    gh_job['services'][srv_alias] = {"image": srv_name}

        # Needs
        needs = value.get('needs', [])
        if needs:
            # We filter out optional needs or needs that point to other stages
            need_list = []
            for n in needs:
                if isinstance(n, str):
                    need_list.append(n.replace(':', '-').replace(' ', '-'))
                elif isinstance(n, dict) and 'job' in n:
                    need_list.append(n['job'].replace(':', '-').replace(' ', '-'))
            if need_list:
                gh_job['needs'] = need_list

        # Variables
        job_vars = value.get('variables', {})
        if job_vars:
            gh_job['env'] = map_variables(job_vars)
            
        # Scripts
        before_script = value.get('before_script') or gitlab_data.get('before_script')
        if before_script:
            script_content = clean_script_steps(before_script)
            script_content = replace_gitlab_vars(script_content)
            gh_job['steps'].append({
                "name": "Before Script",
                "run": script_content
            })
            
        script = value.get('script')
        if script:
            script_content = clean_script_steps(script)
            script_content = replace_gitlab_vars(script_content)
            gh_job['steps'].append({
                "name": "Run Script",
                "run": script_content
            })
            
        after_script = value.get('after_script') or gitlab_data.get('after_script')
        if after_script:
            script_content = clean_script_steps(after_script)
            script_content = replace_gitlab_vars(script_content)
            gh_job['steps'].append({
                "name": "After Script",
                "run": script_content,
                "if": "always()"
            })
            
        # Artifacts
        artifacts = value.get('artifacts', {})
        if artifacts and 'paths' in artifacts:
            paths = "\n".join(artifacts['paths'])
            gh_job['steps'].append({
                "name": "Upload Artifacts",
                "uses": "actions/upload-artifact@v4",
                "with": {
                    "name": f"{safe_job_id}-artifacts",
                    "path": paths
                }
            })

        if gh_job['steps']:
            github_action['jobs'][safe_job_id] = gh_job

    if not github_action['jobs']:
        return

    # Write translated file
    with open(new_filepath, 'w') as out_f:
        # Add comment header
        out_f.write("# Automatically generated by migrate_gitlab_to_github.py\n")
        out_f.write("# Please review the generated actions for correctness.\n\n")
        yaml.dump(github_action, out_f, default_flow_style=False, sort_keys=False)
    
    print(f"Migrated: {filepath} -> {new_filepath}")

def main():
    yaml_files = glob.glob(os.path.join(GITLAB_DIR, '**/*.yml'), recursive=True)
    for filepath in yaml_files:
        process_file(filepath)
    print("Migration complete.")

if __name__ == "__main__":
    main()
