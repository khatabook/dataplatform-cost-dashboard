{{- define "dataplatform-cost-dashboard.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "dataplatform-cost-dashboard.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $name := default .Chart.Name .Values.nameOverride -}}
{{- if contains $name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{- define "dataplatform-cost-dashboard.labels" -}}
app.kubernetes.io/name: {{ include "dataplatform-cost-dashboard.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- range $k, $v := .Values.labels }}
{{ $k }}: {{ $v | quote }}
{{- end }}
{{- end -}}

{{- define "dataplatform-cost-dashboard.selectorLabels" -}}
app.kubernetes.io/name: {{ include "dataplatform-cost-dashboard.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "dataplatform-cost-dashboard.serviceAccountName" -}}
{{- if .Values.serviceAccount.create -}}
{{- default (include "dataplatform-cost-dashboard.fullname" .) .Values.serviceAccount.name -}}
{{- else -}}
{{- default "default" .Values.serviceAccount.name -}}
{{- end -}}
{{- end -}}

{{- define "dataplatform-cost-dashboard.vaultPath" -}}
{{- if .Values.vault.path -}}
{{- .Values.vault.path -}}
{{- else -}}
private/data/{{ .Values.vault.namespace }}/{{ .Values.vault.secretName }}
{{- end -}}
{{- end -}}

{{- define "dataplatform-cost-dashboard.vaultRole" -}}
{{- if .Values.vault.role -}}
{{- .Values.vault.role -}}
{{- else -}}
{{ .Values.vault.namespace }}-{{ .Values.vault.secretName }}
{{- end -}}
{{- end -}}

{{- define "dataplatform-cost-dashboard.vaultAnnotations" -}}
{{- if .Values.vault.enabled }}
vault.hashicorp.com/agent-cache-enable: "true"
vault.hashicorp.com/agent-inject: "true"
vault.hashicorp.com/agent-init-first: "true"
vault.hashicorp.com/agent-pre-populate-only: "true"
vault.hashicorp.com/agent-inject-secret-secrets.txt: {{ include "dataplatform-cost-dashboard.vaultPath" . | quote }}
vault.hashicorp.com/role: {{ include "dataplatform-cost-dashboard.vaultRole" . | quote }}
{{- end }}
{{- with .Values.podAnnotations }}
{{- toYaml . }}
{{- end }}
{{- end -}}
