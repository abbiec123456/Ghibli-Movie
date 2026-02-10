Risk 	Likelihood 	Impact 	Mitigation 

Risk Vulnerable dependency in commit deploys to prod via GitHub Actions 
Likelihood 	Medium 	
Impact High
Mitigation ZAP scanning and Sonarqube scans mitigate likelyhood 

Risk Secret leak in repo or Actions (e.g., DB password) 	
Likelihood 	High 	
Impact Critical 
Mitigation Sonarqube static and zap dynamic scans mitigate this  

Risk SQL injection via Flask routes 	
Likelihood 	Medium 	
Impact High 	
cN/A docker bridge and docker  

Risk SSH brute-force on VPS 	
Likelihood High 	
Impact High 	
Impact Fail2ban mitigates 

Risk DDoS / brute-force on web app 	
Likelihood Medium 	
Impact Medium 	
Mitigation To be implemented 

Risk Unpatched VPS/Docker (e.g., kernel vuln) 	
Likelihood Low 	
Impact High 	
Mitigation Auto-updates via unattended-upgrades 

Risk Exposed Postgres port externally 	
Likelihood Medium 	
Impact Critical 	
Mitigation Bind to localhost; docker bridge willl only expose frontend use