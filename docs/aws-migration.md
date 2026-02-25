# AWS Account Migration Documentation

## Overview

This document tracks migrating the Colandr production data and services from Sam’s AWS account to DataKind’s AWS account. The migration includes the production database, file storage, and deploying the Colandr 2.0 backend on an EC2 instance in DataKind’s account.

## Migration Objectives

1. **Zero Data Loss:** Migrate complete production database with all user data
2. **Minimal Downtime:** Aim for minimal service interruption during migration
3. **Infrastructure Parity:** Replicate the same architecture in DataKind's account
4. **Documentation:** Fully document the new infrastructure for future reference

## Pre-Migration Steps

Before beginning the migration, complete these preparatory tasks:

- [ ] Stop Colandr 1.0 application in Sam's account
- [ ] Prevent end user access to Colandr 1.0
- [ ] Document rollback procedure
- [ ] Schedule maintenance window
- [ ] Notify stakeholders

## Detailed Migration Runbook (incorporating the Google Doc)

This section incorporates a detailed execution plan while keeping the background above.

### 0. Announce the migration

- Prepare the migration announcement page.

### 1. Migrate the database (RDS snapshot)

**Goal:** Restore the production database into DataKind’s account and update the new EC2 instance to use it.

#### 1.1 Take a snapshot in Sam’s account

- Create a snapshot of the production RDS instance in Sam’s account.

#### 1.2 Copy snapshot to `us-east-1`

- Copy the snapshot to `us-east-1` (if the source snapshot is not already there).

#### 1.3 Share snapshot to DataKind’s AWS account

- Share the snapshot with DataKind’s AWS account: `335510308717`.

#### 1.4 Delete the old testing RDS instance (if present)

- Delete any testing DB instance like `colandr-db` that was created during testing so the restored identifier can be reused.

#### 1.5 Restore the DB in DataKind’s account

Restore from “Shared with me” snapshot with these settings (from the detailed plan):

- **Identifier**: `colandr-db`
- **Class**: `db.r8g.xlarge`
- **Multi-AZ**: create a standby instance
- **VPC**: `Colandr`
- **Subnet group**: `colandr-private-subnet-group`
- **Public access**: No
- **VPC security group**: `colandr-rds-sg`

#### 1.6 Update the Colandr EC2 instance to use the new DB endpoint

Update these files on the EC2 instance (names from the detailed plan):

- `~/permanent-colandr-backend/.env`
  - `COLANDR_DATABASE_URI=<NEW_DB_ENDPOINT>`
- `~/.pg_services.conf`
  - `HOST=<NEW_DB_ENDPOINT>`
- `~/.pgpass`
  - Update the host portion to `<NEW_DB_ENDPOINT>:...`

#### 1.7 Run the schema migration script (1.0 → 2.0)

From the backend repo directory:

```bash
cd ~/permanent-colandr-back
docker compose -f compose.prod.yaml run --rm api python scripts/migrate_1_0_to_2_0.py
docker compose -f compose.prod.yaml run --rm api flask db current
```

#### 1.8 Downsize DB after the migration

After verification, modify the restored instance type to `db.t4g.micro`.

### 2. Migrate file data to S3

**Goal:** move the `colandr_data` filesystem content from the old EC2 instance to a bucket, then down to the new instance.

From Sam’s EC2 instance:

```bash
aws s3 sync /home/colandr/permanent-colandr-back/colandr_data/ s3://colandr/
```

From the new EC2 instance:

```bash
aws s3 sync s3://colandr/ ~/colandr_data
```

### 3. Verify migration

Restart the backend service:

```bash
sudo systemctl restart colandr-api.service
```

Verify health:

- `https://v2.colandrapp.com/api/health/`

### 4. Frontend migration (high level)

This repo does not deploy the frontend, but the detailed plan includes:

- Create new site on Forge
- Set `.env` for the frontend:
  - `DK_API_SUITE_URL=https://api.colandrapp.com`
  - database variables as needed

## Validation & Monitoring

**Goal:** Ensure successful migration and system stability

**Immediate Post-Cutover (First 24 hours):**

- [ ] Monitor logs and metrics continuously
- [ ] Verify user access and functionality
- [ ] Check database performance and connectivity
- [ ] Monitor application errors and exceptions
- [ ] Verify background tasks (Celery) are processing correctly
- [ ] Check file storage operations
- [ ] Monitor email delivery

**Extended Monitoring (24-48 hours):**

- [ ] Continue monitoring for 24-48 hours
- [ ] Verify all functionality remains stable
- [ ] Check for any performance degradation
- [ ] Monitor cost implications
- [ ] Collect user feedback

**Validation Checklist:**

- [ ] All API endpoints respond correctly
- [ ] User authentication works
- [ ] Database queries execute successfully
- [ ] Background tasks (Celery) process correctly
- [ ] File uploads/downloads work
- [ ] Email sending works
- [ ] Performance is acceptable
- [ ] Monitoring and logging are operational

## Cleanup & Documentation

**Goal:** Complete migration and update documentation

**Tasks:**

- [ ] Confirm stability in DataKind's account (Colandr 2.0)
- [ ] Keep Colandr 1.0 running in read-only mode for rollback capability
- [ ] Decommission Colandr 1.0 resources in DataKind's account (after validation period)
- [ ] Decommission resources in Sam's account (after validation period)
- [ ] Document final architecture
- [ ] Schedule final decommissioning of Sam's account resources

## Current Infrastructure

### Sam's AWS Account (Source)

**Architecture:**

- EC2 instance (t2.large) running nginx + Express + Python backend
- RDS PostgreSQL 12.22 database
- Security group: sg-0a538efb21a010c71 (Evidence)
- VPC: vpc-39d9c951, Subnet: subnet-4cceb836

**Services:**

- Compute: EC2 t2.large (i-0f5a0546e3cf232f8)
- Database: RDS PostgreSQL (test-ohio-restore)
- Cache: Redis (running on EC2, not ElastiCache)
- Networking: Direct nginx on EC2, no load balancer

### DataKind's AWS Account (Target)

**Architecture:**

**Networking:**

- VPC with public and private subnets
- Public subnet: `Colandr-public` (for EC2 instances)
- Private subnet: `Colandr-private` (for RDS database)
- Security group: `web-host` (for EC2 instances)
- Public Elastic IP address for EC2 instance

**Services (Colandr 2.0 - Production):**

- Compute: New EC2 instance for Colandr 2.0
- Database: Shared RDS instance
- Cache: Redis (running on EC2 or ElastiCache)
- Storage: S3 bucket for file storage
- Networking: TBD (may include ALB for production)

**Key Configurations:**

- _To be documented during setup..._

## Application Components

The Colandr backend consists of the following services:

1. **API Service** (`colandr-api`)
   - Flask application
   - Handles HTTP requests
   - Port: 5000
   - Dockerfile: [`Dockerfile.api`](../Dockerfile.api)

2. **Worker Service** (`colandr-worker`)
   - Celery worker
   - Processes background tasks
   - Dockerfile: [`Dockerfile.worker`](../Dockerfile.worker)

3. **Database** (`db`)
   - PostgreSQL 17
   - Stores all application data
   - Requires full migration with data

4. **Cache/Broker** (`broker`)
   - Redis 8.0
   - Celery message broker
   - Task result backend

5. **Email Service** (optional in production)
   - Development: Mailpit
   - Production: Likely SES or SMTP
