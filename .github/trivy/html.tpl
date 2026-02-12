<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Trivy Security Report</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; margin: 0; padding: 20px; background: #f6f8fa; color: #24292e; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 6px; box-shadow: 0 1px 3px rgba(0,0,0,0.12); }
        h1 { border-bottom: 1px solid #eaecef; padding-bottom: 10px; margin-bottom: 20px; }
        .summary { display: flex; gap: 20px; margin-bottom: 30px; }
        .card { flex: 1; padding: 15px; border-radius: 6px; color: white; text-align: center; }
        .bg-critical { background-color: #cb2431; }
        .bg-high { background-color: #d73a49; }
        .bg-medium { background-color: #d15704; }
        .bg-low { background-color: #ffc107; color: black; }
        .bg-unknown { background-color: #6a737d; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { text-align: left; padding: 12px; border-bottom: 1px solid #eaecef; }
        th { background-color: #f6f8fa; font-weight: 600; }
        tr:hover { background-color: #f1f8ff; }
        .severity-badge { padding: 4px 8px; border-radius: 4px; color: white; font-size: 12px; font-weight: 600; display: inline-block; }
        .links a { color: #0366d6; text-decoration: none; }
        .links a:hover { text-decoration: underline; }
        details { margin-bottom: 10px; }
        summary { cursor: pointer; font-weight: bold; margin-bottom: 5px; outline: none; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Trivy Security Report</h1>
        <p><strong>Date:</strong> {{ .CreatedAt }}</p>
        <p><strong>Artifact:</strong> {{ .ArtifactName }}</p>

        {{- $critical := 0 }}{{- $high := 0 }}{{- $medium := 0 }}{{- $low := 0 }}{{- $unknown := 0 }}
        {{- range .Results }}
            {{- range .Vulnerabilities }}
                {{- if eq .Severity "CRITICAL" }}{{ $critical = add $critical 1 }}{{ end }}
                {{- if eq .Severity "HIGH" }}{{ $high = add $high 1 }}{{ end }}
                {{- if eq .Severity "MEDIUM" }}{{ $medium = add $medium 1 }}{{ end }}
                {{- if eq .Severity "LOW" }}{{ $low = add $low 1 }}{{ end }}
                {{- if eq .Severity "UNKNOWN" }}{{ $unknown = add $unknown 1 }}{{ end }}
            {{- end }}
        {{- end }}

        <div class="summary">
            <div class="card bg-critical"><h3>{{ $critical }}<br>CRITICAL</h3></div>
            <div class="card bg-high"><h3>{{ $high }}<br>HIGH</h3></div>
            <div class="card bg-medium"><h3>{{ $medium }}<br>MEDIUM</h3></div>
            <div class="card bg-low"><h3>{{ $low }}<br>LOW</h3></div>
            <div class="card bg-unknown"><h3>{{ $unknown }}<br>UNKNOWN</h3></div>
        </div>

        {{- range .Results }}
        <details open>
            <summary>Target: {{ .Target }} ({{ len .Vulnerabilities }} vulnerabilities)</summary>
            {{- if .Vulnerabilities }}
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Severity</th>
                        <th>Package</th>
                        <th>Installed</th>
                        <th>Fixed</th>
                        <th>Title</th>
                    </tr>
                </thead>
                <tbody>
                    {{- range .Vulnerabilities }}
                    <tr>
                        <td><a href="{{ .PrimaryURL }}" target="_blank">{{ .VulnerabilityID }}</a></td>
                        <td><span class="severity-badge bg-{{ .Severity | lower }}">{{ .Severity }}</span></td>
                        <td>{{ .PkgName }}</td>
                        <td>{{ .InstalledVersion }}</td>
                        <td>{{ .FixedVersion }}</td>
                        <td>{{ .Title }}</td>
                    </tr>
                    {{- end }}
                </tbody>
            </table>
            {{- else }}
            <p>No vulnerabilities found.</p>
            {{- end }}
        </details>
        {{- end }}
    </div>
</body>
</html>
