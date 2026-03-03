# Ghibli Movie Application

## Architecture Overview

---

## Architecture Overview

### Application Stack
- **Type**: Python Web Application (Flask/Django)  
- **Name**: Studio Ghibli Movie Maker  
- **Deployment**: Docker containerized  
- **Web Server**: Gunicorn (4 workers, port 80)  
- **Database**: PostgreSQL 16  
- **Monitoring**: New Relic APM  

### Infrastructure Components

1. **Web Application Layer**  
   - Container: `ghibli-app` (`ghcr.io/abbiec123456/ghibli-movie:pr-31`)  
   - Running on port **80 (HTTP)**  
   - Gunicorn WSGI server with **4 workers**  
   - **Status**: Healthy with 12+ hours uptime  

2. **Database Layer**  
   - PostgreSQL **16** database: `ghibli_booking`  
   - User: `ghibli_adm`  
   - Tables: `admins`, `booking_modules`, `bookings`, `course_modules`, `courses`, `customers`  

3. **Container Runtime**  
   - **Docker Engine** (6+ days uptime)  
   - **Single container deployment**  

4. **Monitoring**  
   - **New Relic Browser Agent** for APM  
   - Session replay and error tracking **enabled**

