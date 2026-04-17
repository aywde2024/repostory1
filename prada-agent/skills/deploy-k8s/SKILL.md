---
name: deploy-k8s
description: Deploy services to Kubernetes with health checks
version: 1.2.0
platforms: [linux, macos]
metadata:
  prada:
    tags: [kubernetes, devops, deployment]
    category: infrastructure
    fallback_for_toolsets: [web]
    requires_toolsets: [terminal]
    config:
      - key: k8s.namespace
        description: "Default Kubernetes namespace"
        default: "default"
        prompt: "Enter default namespace:"
      - key: k8s.context
        description: "Kubectl context name"
        default: "production"
        prompt: "Enter kubectl context:"
    required_environment_variables:
      - name: KUBECONFIG
        prompt: "Path to kubeconfig file"
        help: "Usually ~/.kube/config or provided by cloud provider"
        required_for: "full functionality"
---

# Deploy to Kubernetes

## When to Use
- Deploying a new microservice to staging/production
- Updating an existing deployment with new image tag
- Rolling back a failed deployment

## Procedure
1. Validate manifest with `kubectl apply --dry-run=client -f <file>`
2. Check cluster resources: `kubectl describe nodes`
3. Apply with server-side apply: `kubectl apply --server-side -f <file>`
4. Verify rollout: `kubectl rollout status deployment/<name>`
5. Check pods: `kubectl get pods -l app=<label> -w`

## Pitfalls
- ❌ Never use `kubectl apply -f .` (applies all manifests)
- ⚠️ Staging uses namespace `staging`, production uses `prod`
- 🔑 KUBECONFIG must point to correct cluster context

## Verification
```bash
# Check deployment status
kubectl get deployment <name> -n ${K8S_NAMESPACE:-default}

# Verify pods are running
kubectl get pods -l app=<name> -n ${K8S_NAMESPACE:-default} --field-selector=status.phase=Running

# Test endpoint (if service exposed)
curl -s https://<service>.example.com/health
```

## References
- [Kubernetes Deployment Docs](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/)
- [kubectl Cheat Sheet](https://kubernetes.io/docs/reference/kubectl/cheatsheet/)
