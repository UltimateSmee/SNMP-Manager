import json
import schedule
import time
# time for scheduling? 
import sqlite3
import sys
from pysnmp.hlapi import *
from pysnmp import debug
from ping3 import ping

def network_discovery(ips):
	# Ping all IP's on network
	return

def ping_device(ip):
	# Ping device, return true if it is reachable
	try:
		if ping(ip, timeout=4):
			print(f"Device at {ip} IS reachable.")
			return True
		
	except Exception as e:
		print(f"Error during Ping: {str(e)}")

	print(f"Device at {ip} IS NOT reachable.")
	return False

def check_snmp(ip):
	try:
		getCmd(
			SnmpEngine(),
			CommunityData("public"),
			UdpTransportTarget((ip, 161)),
			ContextData(),
			ObjectType(ObjectIdentity("1.3.6.1.2.1.1.5.0"))
		)
		print(f"{ip} is available for SNMP query")
		return True
	
	except Exception as e:
		print(str(e))
		print(f"Unable to query SNMP on {ip}")

	return False

def query_database():
	# Connect to the database and create cursor
	conn = sqlite3.connect('network_monitor.db')
	cursor = conn.cursor()

	# Execute SELECT * with cursor to select all data in snmp_data
	cursor.execute('SELECT * FROM snmp_data')

	# Fetch all rows from cursor selection
	rows = cursor.fetchall()

	# Print header row
	print("{0:>5} {1:<20} {2:<15} {3:<20} {4:<15} {5:<15}".format("ID", "Timestamp", "IP Address", "Community", "OID", "Value"))
	print("="*90)

	# Print each row of data
	for row in rows:
		print("{0:>5} {1:<20} {2:<15} {3:<20} {4:<15} {5:<15}".format(*row))

	# Close out the connection
	conn.close()


def get_snmp_data(ip, community, oid):

# Initialize SQLite Database & Cursor
	conn = sqlite3.connect('network_monitor.db')
	cursor = conn.cursor()

# Create a table to store SNMP data
	cursor.execute('''
		CREATE TABLE IF NOT EXISTS snmp_data (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
			ip_address TEXT,
			community STRING,
			oid STRING,
			value STRING
		)
	''')

# Maximum amount of iterations for snmpwalk (nextCmd()) command
	mx = 100
	iterator = bulkCmd(
			SnmpEngine(),
			CommunityData(community),
			UdpTransportTarget((ip, 161)),
			ContextData(),
			0, 25,
			ObjectType(ObjectIdentity(oid)),
			lexicographicMode=False
		)
	try:
		for i in range(mx):
			errorIndication, errorStatus, errorIndex, varBinds = next(iterator)
			
			if errorIndication or errorStatus:
				print(f"Error Indication: {errorIndication} {errorStatus}")
				return
			
			else:
				if not varBinds:
					print(f"No values returned for OID {oid}")
				else:
					for varBind in varBinds:
						# Cases where it returns nothing, format the output to be more readable
						if not varBinds:
							print(f"{str(varBind)[str(varBind).rfind('No Such'):]}: {varBind[0]} ( {str(varBind)[12:str(varBind).rfind('No Such')-2]} )")
						else:
							print(f"{varBind[0]} = {varBind[1]}")

						
			cursor.execute('''INSERT INTO snmp_data(ip_address, community, oid, value) VALUES(?, ?, ?, ?)''', (ip, community, oid, varBind[1].prettyPrint()))
			i+=1

	except StopIteration:
		return

	except Exception as e:
		# Common errors with error numbers will be displayed rather than the whole output
		t = str(e).rfind('[Errno')
		if t != -1:
			e = str(e)[t:]
		
		print(f"\n	Error during SNMP query: \n	Device: {ip} \n	Error: {str(e)}\n")

# Commit Changes and close connection

	conn.commit()
	conn.close()


def add_device(ip, community, oids=[]):

# Load current list of devices
	try:
		with open('devices.json', 'r') as file:
			devices = json.load(file)
	except FileNotFoundError:
		devices = []

# Check if device exists already
	d = 0
	for device in devices:
		if device["ip"] == ip:
			print(f"Device with IP {ip} already exists.")

# If more than one oid, append to ip
			o = len(device["oids"]) - 1
			for oid in oids:
				if oid in device["oids"]:
					print(f"Oid {oid} for device with ip {ip} already exists")
					continue

				device["oids"].append(oid)
				print(f"Oid, {oid} added to device with ip {ip}")
				o+=1

			with open('devices.json', 'w') as file:
				json.dump(devices, file, indent=2)
			
			return
		d+=1
			


# Continue to add device to list if it doesnt exist

	new_device = {"ip": ip, "community": community, "oids": oids}
	devices.append(new_device)

	with open('devices.json', 'w') as file:
		json.dump(devices, file, indent=2)

	print(f"Device with IP {ip} added successfully.")


def job():
# ADD ABILITY TO RUN SELECTED DEVICES. CHECK FOR DEVICE, IF NOT FOUND, ASK IF WANT TO ADD THEN RUN FOR THAT DEVICE
# ADD RUN ALL VS RUN ONE
# Load devices from devices.json
	try:
		with open('devices.json', 'r') as file:
			devices = json.load(file)
	except FileNotFoundError:
		devices = []

# Check for devices to query
	if not devices:
		print("No devices to query.")
		return


# Query each device
	for device in devices:
		ip, community = device["ip"], device["community"]
		for oid in device["oids"]:
			get_snmp_data(ip, community, oid)

schedule.every(5).seconds.do(job)
	

if __name__ == "__main__":

	usage = """Usage:
python3 snmp_monitor.py [options] [[IP's], [IP, Community, OID], [OID's]]...

	ping	To check device, or networks', availability:	python3 snmp_monitor.py PING <<ip> OR <ip/CIDR> OR <ip AND NETMASK>>
	query	To run query on all devices in devices.json:	python3 snmp_monitor.py QUERY
	run 	To run snmp query on device: 	python3 snmp_monitor.py <ip> <community> <oid> 
	add 	To add a new device:	python3 snmp_monitor.py ADD <ip> <community> <oids...>
	"""

	# Store length of command line variables to be checked later
	l = len(sys.argv)
	##############################################
	#debug.setLogger(debug.Debug('all'))
	##############################################
	# Determine which funtion to run based on command line arguments
	if l == 2:
		if "run" in sys.argv:
			job()
			
		elif "query" in sys.argv:
			query_database()
		else:
			print(usage)
		
	elif l == 3:	
		if "ping" in sys.argv:
			for i in range(l-2):
				# Ping device for connectivity
				ip = sys.argv[i-1]
				if ping_device(ip):
					check_snmp(ip)
		else:
			print(usage)

	elif l == 4:
		ip, community, oid = sys.argv[1], sys.argv[2], sys.argv[3]
		get_snmp_data(ip, community, oid)

	elif "add" in sys.argv:
			ip, community = sys.argv[2], sys.argv[3]
			oids=[]
			for o in range(l-4):
				oids.append(sys.argv[4+o])
			add_device(ip, community, oids)

	else:
		print(usage)
		sys.exit(1)

