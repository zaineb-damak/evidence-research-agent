{{/* Naming, labels and the derived connection strings every workload needs. */}}

{{- define "research-agent.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "research-agent.fullname" -}}
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

{{- define "research-agent.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "research-agent.selectorLabels" -}}
app.kubernetes.io/name: {{ include "research-agent.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "research-agent.labels" -}}
helm.sh/chart: {{ include "research-agent.chart" . }}
{{ include "research-agent.selectorLabels" . }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: research-agent
{{- end -}}

{{/*
Component-scoped labels. Call with a dict: (dict "root" $ "component" "api").
The component label is what Services select on and what splits dashboards.
*/}}
{{- define "research-agent.componentSelectorLabels" -}}
{{ include "research-agent.selectorLabels" .root }}
app.kubernetes.io/component: {{ .component }}
{{- end -}}

{{- define "research-agent.componentLabels" -}}
{{ include "research-agent.labels" .root }}
app.kubernetes.io/component: {{ .component }}
{{- end -}}

{{- define "research-agent.serviceAccountName" -}}
{{- if .Values.serviceAccount.create -}}
{{- default (include "research-agent.fullname" .) .Values.serviceAccount.name -}}
{{- else -}}
{{- default "default" .Values.serviceAccount.name -}}
{{- end -}}
{{- end -}}

{{/* Image reference. Call with (dict "repository" … "root" $). */}}
{{- define "research-agent.image" -}}
{{- $tag := .root.Values.image.tag | default .root.Chart.AppVersion -}}
{{- printf "%s:%s" .repository $tag -}}
{{- end -}}

{{- define "research-agent.configMapName" -}}
{{ include "research-agent.fullname" . }}-config
{{- end -}}

{{/* Chart-derived connection values; always chart-owned. */}}
{{- define "research-agent.connectionSecretName" -}}
{{ include "research-agent.fullname" . }}-connection
{{- end -}}

{{/* API keys and the JWT secret; chart-owned only when secrets.create. */}}
{{- define "research-agent.credentialsSecretName" -}}
{{- if .Values.secrets.existingSecret -}}
{{ .Values.secrets.existingSecret }}
{{- else -}}
{{ include "research-agent.fullname" . }}-credentials
{{- end -}}
{{- end -}}

{{/* --- stateful dependency names ----------------------------------------- */}}

{{- define "research-agent.postgres.fullname" -}}
{{ include "research-agent.fullname" . }}-postgres
{{- end -}}

{{- define "research-agent.neo4j.fullname" -}}
{{ include "research-agent.fullname" . }}-neo4j
{{- end -}}

{{- define "research-agent.qdrant.fullname" -}}
{{ include "research-agent.fullname" . }}-qdrant
{{- end -}}

{{- define "research-agent.redis.fullname" -}}
{{ include "research-agent.fullname" . }}-redis
{{- end -}}

{{/*
Connection strings, derived once here so a workload never has to know whether a
dependency is in-cluster or managed. `required` turns a missing external
endpoint into a clear install-time error rather than a CrashLoopBackOff.
*/}}

{{- define "research-agent.postgresDsn" -}}
{{- if .Values.postgres.enabled -}}
{{- printf "postgresql+psycopg://%s:%s@%s:%v/%s"
      .Values.postgres.auth.username
      .Values.postgres.auth.password
      (include "research-agent.postgres.fullname" .)
      .Values.postgres.service.port
      .Values.postgres.auth.database -}}
{{- else -}}
{{- required "postgres.externalDsn is required when postgres.enabled is false" .Values.postgres.externalDsn -}}
{{- end -}}
{{- end -}}

{{- define "research-agent.neo4jUri" -}}
{{- if .Values.neo4j.enabled -}}
{{- printf "bolt://%s:%v" (include "research-agent.neo4j.fullname" .) .Values.neo4j.service.boltPort -}}
{{- else -}}
{{- required "neo4j.externalUri is required when neo4j.enabled is false" .Values.neo4j.externalUri -}}
{{- end -}}
{{- end -}}

{{- define "research-agent.neo4jPassword" -}}
{{- required "neo4j.auth.password is required" .Values.neo4j.auth.password -}}
{{- end -}}

{{- define "research-agent.qdrantUrl" -}}
{{- if .Values.qdrant.enabled -}}
{{- printf "http://%s:%v" (include "research-agent.qdrant.fullname" .) .Values.qdrant.service.httpPort -}}
{{- else -}}
{{- required "qdrant.externalUrl is required when qdrant.enabled is false" .Values.qdrant.externalUrl -}}
{{- end -}}
{{- end -}}

{{- define "research-agent.redisUrl" -}}
{{- if .Values.redis.enabled -}}
{{- printf "redis://%s:%v/0" (include "research-agent.redis.fullname" .) .Values.redis.service.port -}}
{{- else -}}
{{- required "redis.externalUrl is required when redis.enabled is false" .Values.redis.externalUrl -}}
{{- end -}}
{{- end -}}

{{/*
envFrom shared by the API, the worker and the migration Job: one ConfigMap for
settings, one Secret for credentials. Listing 30 env vars per workload would
drift between them.
*/}}
{{- define "research-agent.envFrom" -}}
- configMapRef:
    name: {{ include "research-agent.configMapName" . }}
- secretRef:
    name: {{ include "research-agent.connectionSecretName" . }}
- secretRef:
    name: {{ include "research-agent.credentialsSecretName" . }}
{{- end -}}

{{/*
Writable scratch space. Every image runs with a read-only root filesystem, so
anything that writes needs an explicit emptyDir.
*/}}
{{- define "research-agent.tmpVolume" -}}
- name: tmp
  emptyDir: {}
{{- end -}}

{{- define "research-agent.tmpVolumeMount" -}}
- name: tmp
  mountPath: /tmp
{{- end -}}
