# SSH Tunnel to Google Cloud VM PostgreSQL
# Project: conductive-bot-483808-a9 (my-pos)
$VM_NAME = "pos-instacd"             # Your VM instance name
$ZONE = "us-central1-a"              # VM zone
$LOCAL_PORT = 5433                   # Local port for tunnel
$REMOTE_PORT = 5432                  # PostgreSQL port on VM

Write-Host "Creating SSH tunnel to PostgreSQL on VM..." -ForegroundColor Green
Write-Host "Once connected, use these pgAdmin settings:" -ForegroundColor Yellow
Write-Host "  Host: localhost (or 127.0.0.1)" -ForegroundColor Cyan
Write-Host "  Port: $LOCAL_PORT" -ForegroundColor Cyan
Write-Host "  Database: pos_inventory" -ForegroundColor Cyan
Write-Host "  Username: pos_inventory" -ForegroundColor Cyan
Write-Host "  Password: 9491316460Aa!" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C to close the tunnel" -ForegroundColor Red
Write-Host ""

# Create SSH tunnel using gcloud (without IAP - using external IP)
gcloud compute ssh $VM_NAME --zone=$ZONE --ssh-flag="-L" --ssh-flag="${LOCAL_PORT}:localhost:${REMOTE_PORT}" --ssh-flag="-N"
