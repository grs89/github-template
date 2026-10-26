package devsecops.security

default allow = false

# Regla de evaluación general: solo se permite si no hay violaciones
allow {
    count(violation_ssh_open) == 0
    count(violation_rdp_open) == 0
    count(violation_non_root_k8s) == 0
    count(violation_latest_tag_k8s) == 0
    count(violation_s3_public) == 0
}

# 1. Seguridad Cloud: Prohibir Security Groups con puerto 22 (SSH) abierto a 0.0.0.0/0
violation_ssh_open[msg] {
    some rule in input.security_group_rules
    rule.cidr_blocks[_] == "0.0.0.0/0"
    rule.from_port <= 22
    rule.to_port >= 22
    msg := sprintf("Seguridad Crítica (Terraform): Puerto SSH (22) expuesto a 0.0.0.0/0 en regla '%v'", [rule.id])
}

# 2. Seguridad Cloud: Prohibir Security Groups con puerto 3389 (RDP) abierto a 0.0.0.0/0
violation_rdp_open[msg] {
    some rule in input.security_group_rules
    rule.cidr_blocks[_] == "0.0.0.0/0"
    rule.from_port <= 3389
    rule.to_port >= 3389
    msg := sprintf("Seguridad Crítica (Terraform): Puerto RDP (3389) expuesto a 0.0.0.0/0 en regla '%v'", [rule.id])
}

# 3. Seguridad K8s: Contenedores deben ejecutar como non-root
violation_non_root_k8s[msg] {
    input.kind in ["Pod", "Deployment", "DaemonSet", "StatefulSet"]
    containers := object.get(input.spec, "containers", object.get(object.get(input.spec, "template", {}).spec, "containers", []))
    container := containers[_]
    not container.securityContext.runAsNonRoot
    msg := sprintf("Seguridad K8s: El contenedor '%v' debe especificar runAsNonRoot: true en securityContext", [container.name])
}

# 4. Seguridad K8s: Prohibir tag :latest en imágenes
violation_latest_tag_k8s[msg] {
    input.kind in ["Pod", "Deployment", "DaemonSet", "StatefulSet"]
    containers := object.get(input.spec, "containers", object.get(object.get(input.spec, "template", {}).spec, "containers", []))
    container := containers[_]
    endswith(container.image, ":latest")
    msg := sprintf("Gobernanza K8s: El contenedor '%v' usa el tag ':latest' (%v). Debe usar versión fija.", [container.name, container.image])
}

# 5. Seguridad Terraform: Prohibir S3 Buckets públicos
violation_s3_public[msg] {
    resource := input.resource_changes[_]
    resource.type == "aws_s3_bucket_acl"
    resource.change.after.acl in ["public-read", "public-read-write"]
    msg := sprintf("Seguridad Crítica (Terraform): El bucket S3 '%v' tiene ACL pública '%v'", [resource.name, resource.change.after.acl])
}
