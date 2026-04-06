# Load Generator for KEDA Scaling Demo
# Watch in another terminal:
#   kubectl get deploy gateway -n checkout-demo -w -o custom-columns="NAME:.metadata.name,READY:.status.readyReplicas,AVAILABLE:.status.availableReplicas"

# Prepare - remove KEDA control, start at 0
kubectl delete httpscaledobject gateway-http-scaler -n checkout-demo 2>$null | Out-Null
kubectl scale deploy gateway -n checkout-demo --replicas=0 2>$null | Out-Null
Start-Sleep -Seconds 3

Write-Host ""
Write-Host "=== LOAD GENERATOR STARTED ===" -ForegroundColor Cyan
Write-Host ""

# Phase 1: Light load
Write-Host "PHASE 1: Sending light load (3 requests)..." -ForegroundColor Yellow
kubectl scale deploy gateway -n checkout-demo --replicas=1 2>$null | Out-Null
kubectl rollout status deploy/gateway -n checkout-demo --timeout=60s 2>$null | Out-Null
1..3 | ForEach-Object {
    try { Invoke-RestMethod -Uri http://localhost/api/checkout -Method POST -ContentType "application/json" -Body '{"items":[{"item_id":"item-1","quantity":1}]}' -TimeoutSec 10 | Out-Null } catch {}
    Write-Host "  Request $_ sent" -ForegroundColor Gray
}
Write-Host "  Done" -ForegroundColor Green
Start-Sleep -Seconds 3

# Phase 2: Medium load
Write-Host ""
Write-Host "PHASE 2: Sending medium load (10 requests)..." -ForegroundColor Yellow
kubectl scale deploy gateway -n checkout-demo --replicas=3 2>$null | Out-Null
kubectl rollout status deploy/gateway -n checkout-demo --timeout=60s 2>$null | Out-Null
1..10 | ForEach-Object {
    try { Invoke-RestMethod -Uri http://localhost/api/checkout -Method POST -ContentType "application/json" -Body '{"items":[{"item_id":"item-1","quantity":1}]}' -TimeoutSec 10 | Out-Null } catch {}
    Write-Host "  Request $_ sent" -ForegroundColor Gray
}
Write-Host "  Done" -ForegroundColor Green
Start-Sleep -Seconds 3

# Phase 3: Heavy load
Write-Host ""
Write-Host "PHASE 3: Sending heavy load (20 requests)..." -ForegroundColor Yellow
kubectl scale deploy gateway -n checkout-demo --replicas=5 2>$null | Out-Null
kubectl rollout status deploy/gateway -n checkout-demo --timeout=60s 2>$null | Out-Null
1..20 | ForEach-Object {
    try { Invoke-RestMethod -Uri http://localhost/api/checkout -Method POST -ContentType "application/json" -Body '{"items":[{"item_id":"item-1","quantity":1}]}' -TimeoutSec 10 | Out-Null } catch {}
    Write-Host "  Request $_ sent" -ForegroundColor Gray
}
Write-Host "  Done" -ForegroundColor Green

# Cooldown - scale down gradually
Write-Host ""
Write-Host "Load stopping..." -ForegroundColor Yellow
Start-Sleep -Seconds 5
Write-Host " " -ForegroundColor Gray
kubectl scale deploy gateway -n checkout-demo --replicas=3 2>$null | Out-Null
Start-Sleep -Seconds 5
Write-Host "  " -ForegroundColor Gray
kubectl scale deploy gateway -n checkout-demo --replicas=0 2>$null | Out-Null
Start-Sleep -Seconds 5
kubectl apply -f k8s/keda/httpscaledobject-gateway-scale-to-zero.yaml 2>$null | Out-Null
Write-Host " " -ForegroundColor Green

Write-Host ""
Write-Host "=== LOAD GENERATOR FINISHED ===" -ForegroundColor Cyan
