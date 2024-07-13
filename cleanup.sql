
DELETE FROM event
WHERE 
	startdate IS NULL OR
	enddate IS NULL OR
	enddate < DATE('now', '-7  days');
