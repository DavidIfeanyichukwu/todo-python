# Question 2 — To-Do List Microservices (Python) — Deployment Guide

Two Python (Flask) microservices on ECS Fargate behind an ALB, provisioned by the
single CloudFormation template. Matches the lecturer's template conventions:
frontend port **3000**, backend port **5000**, image URIs passed as parameters,
two-pass deployment via `DesiredCount`.

```
todo-python/
├── frontend/          app.py (Flask web app) + Dockerfile + requirements.txt
├── backend/           app.py (Flask REST API) + Dockerfile + requirements.txt
└── infrastructure/    cloudformation.yaml (single template — lecturer's)
```

**Prerequisites:** AWS CLI configured, Docker Desktop running. Commands are PowerShell.

---

## Step 0 — Variables

```powershell
$Region    = "ap-southeast-2"
$Stack     = "todo-app"
$AccountId = (aws sts get-caller-identity --query Account --output text)
$Registry  = "$AccountId.dkr.ecr.$Region.amazonaws.com"
cd todo-python
```

## Step 1 — Deploy the stack (DesiredCount=0, placeholder images)

The template creates the ECR repositories that the task definitions will later pull
from — a chicken-and-egg solved by deploying first with **DesiredCount=0** (all
resources created, no tasks started), pushing the images, then updating the stack.

```powershell
aws cloudformation deploy `
  --region $Region --stack-name $Stack `
  --template-file infrastructure/cloudformation.yaml `
  --capabilities CAPABILITY_NAMED_IAM
```

(Defaults already have DesiredCount=0 and placeholder image URIs.
`CAPABILITY_NAMED_IAM` is required because the roles have explicit names.)

📸 CloudFormation console: stack `CREATE_COMPLETE` + Resources tab.

## Step 2 — Build and push both Python images

```powershell
aws ecr get-login-password --region $Region | docker login --username AWS --password-stdin $Registry

docker build -t "$Registry/todo-app-backend:latest" ./backend
docker push  "$Registry/todo-app-backend:latest"

docker build -t "$Registry/todo-app-frontend:latest" ./frontend
docker push  "$Registry/todo-app-frontend:latest"
```

📸 ECR console: both repositories showing the `latest` image.

## Step 3 — Start the services with the real images

```powershell
aws cloudformation deploy `
  --region $Region --stack-name $Stack `
  --template-file infrastructure/cloudformation.yaml `
  --capabilities CAPABILITY_NAMED_IAM `
  --parameter-overrides DesiredCount=1 `
    FrontendImageUri="$Registry/todo-app-frontend:latest" `
    BackendImageUri="$Registry/todo-app-backend:latest"
```

Allow 2–3 minutes for tasks to start and ALB health checks (`/health` on both
services) to pass.

## Step 4 — Validate

```powershell
$AlbDns = aws cloudformation describe-stacks --region $Region --stack-name $Stack `
  --query "Stacks[0].Outputs[?OutputKey=='ALBDNSName'].OutputValue" --output text
$Url = "http://$AlbDns"
$Url

aws ecs describe-services --region $Region --cluster todo-app-cluster `
  --services todo-app-frontend-service todo-app-backend-service `
  --query "services[].{name:serviceName,desired:desiredCount,running:runningCount}"

curl "$Url/health"        # frontend, via ALB default rule
curl "$Url/api/health"    # backend, via ALB /api/* rule
curl "$Url/api/todos"     # live data from the backend
```

Open `$Url` in a browser: the To-Do page loads from the Frontend Service and
immediately fetches the item list from the Backend Service through the ALB's
`/api/*` rule — add, toggle, and delete items to prove the full round trip.

📸 **For the rubric's "Validation Evidence — flawless":**
1. Browser at the ALB URL **with the address bar clearly showing the ALB DNS name**
   and the app displaying items (this is the money shot).
2. Add an item and capture it appearing in the list (frontend↔backend proof).
3. ECS console: both services 1/1 running.
4. Both target groups healthy.
5. PowerShell output of `curl "$Url/api/todos"`.

## Step 5 — Tear down

The ALB bills (~US$0.025/hr) while it exists. The template's ECR repositories do
not have `EmptyOnDelete`, so empty them before deleting or the delete fails:

```powershell
aws ecr batch-delete-image --region $Region --repository-name todo-app-frontend --image-ids imageTag=latest
aws ecr batch-delete-image --region $Region --repository-name todo-app-backend  --image-ids imageTag=latest
aws cloudformation delete-stack --region $Region --stack-name $Stack
aws cloudformation wait stack-delete-complete --region $Region --stack-name $Stack
```

---

## Design write-up (rubric: justify each service, separate ECRs, security groups, ALB)

> Adapt to your own voice before submitting.

I containerised each microservice with its own Dockerfile on the `python:3.12-slim`
base image, installing pinned dependencies in a cached layer, running the
application as a non-root user, and serving Flask through gunicorn (a production
WSGI server) — producing lightweight, portable images of roughly 150 MB. Each
service has its **own ECR repository** because the two services version, scan, and
deploy independently: a new backend release can never overwrite or interfere with
the frontend image, each repository carries its own vulnerability-scan history, and
lifecycle policies can differ per service — the independence that justifies a
microservices architecture. Every AWS resource is defined in a **single declarative
CloudFormation template** with parameters (`AppName`, container ports, image URIs,
`DesiredCount`), making the whole environment repeatable in any account or region;
the `DesiredCount` parameter also sequences deployment cleanly (create
infrastructure at 0, push images, update to 1). I chose **ECS on Fargate** so there
are no EC2 hosts to patch or scale — AWS supplies the compute per task — and each
task runs in `awsvpc` mode with its own network interface, which is why the target
groups use IP targeting.

The **Application Load Balancer** is the single public entry point and serves three
purposes: it distributes traffic across tasks in two Availability Zones (the
resilience requirement), it health-checks both services (`/health`) so failed
containers are replaced automatically, and its path-based routing sends `/api/*` to
the Backend and everything else to the Frontend — giving the browser one origin, so
the frontend's JavaScript calls the backend with no CORS configuration. **Security
groups** enforce the traffic flow in layers: the ALB's group accepts only HTTP 80
from the internet, and the ECS tasks' group accepts traffic solely from the ALB's
security group (referenced by group ID rather than CIDR) on the two container
ports — no path exists to a container except through the load balancer. **IAM
follows least privilege with two distinct roles**: the task execution role lets the
Fargate agent pull images from ECR and write to CloudWatch Logs, while the task
role — assumed by the application code itself — carries no permissions because the
app needs no AWS API access; log groups with 7-day retention complete the
observability picture. Tasks currently run in the public subnets for simplicity and
cost; the template already provisions private subnets, and the production hardening
step would move tasks there behind a NAT Gateway or VPC endpoints so containers
hold no public IPs.

---

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| Service events: "unable to pull image" | Image not pushed, wrong URI parameter, or wrong region |
| Tasks start then cycle unhealthy | Health check path/port mismatch — both TGs expect `/health` on 3000 (frontend) and 5000 (backend) |
| `CREATE_FAILED` at DesiredCount>0 first time | Skipped the DesiredCount=0 pass — images didn't exist yet |
| Page loads, "Backend API unreachable" | `/api/*` listener rule or backend target health — check the backend TG |
| `delete-stack` fails on ECR | Repos not emptied first (Step 5) |
| IAM role name conflict on re-deploy | Named roles from a failed earlier stack — delete that stack fully first |
