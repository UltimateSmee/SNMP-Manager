import json
import schedule
import time
import sqlite3
import sys
from pysnmp.hlapi import *



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
	try: 
		errorIndication, errorStatus, errorIndex, varBinds = next(getCmd(
			SnmpEngine(),
			CommunityData(community),
			UdpTransportTarget((ip, 161)),
			ContextData(),
			ObjectType(ObjectIdentity(oid)
		)))

		if errorIndication:
			print(f"Error: {errorIndication}")
		elif errorStatus:
			print(f"Error: {errorStatus}")
		else:
			if not varBinds:
				print(f"No values returned for OID {oid}")
			else:
				for varBind in varBinds:
					print(f"{varBind[0]} = {varBind[1]}")

		cursor.execute('''
			INSERT INTO snmp_data(ip_address, community, oid, value)
			VALUES(?, ?, ?, ?)
		''', (ip, community, oid, varBind[1].prettyPrint()))

	except Exception as e:
		print(f"Error during SNMP query: {str(e)}")

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
			for arg in oids:
				if arg in device:
					print(f"Oid {arg} for device with ip {ip} already exists")
					continue

				new_oid = {"oid"+arg: arg}
				print(devices)
				devices[d].append(new_oid)

			with open('devices.json', 'w') as file:
				json.dump(devices, file, indent=2)
			print(f"Device oid {arg} added to ip {ip}")
			return



# Continue to add device to list 

	new_device = {"ip": ip, "community": community, "oid": oids[0]}
	devices.append(new_device)

	with open('devices.json', 'w') as file:
		json.dump(devices, file, indent=2)

	print(f"Device with IP {ip} added successfully.")



def job():

# Load devices from devices.json
	try:
		with open('devices.json', 'r') as file:
			devices = json.load(file)
	except FileNotFouandError:
		devices = []

# Check for devices to query
	if not Devices:
		print("No devices to query.")
		return


# Query each device
	for device in devices:
		ip, community, oid = device["ip"], device["community"], device["oid"]
		get_snmp_data(ip, community, oid)


schedule.every(5).seconds.do(job)


if __name__ == "__main__":
	if (len(sys.argv) != 4 and ("add" not in sys.argv)):
		print(f"""Usage:
			To run query on all devices in devices.json: python3 snmp_monitor.py 
			To run query on device: python3 snmp_monitor.py <ip> <community> <oid> 
			To add a new device: python3 snmp_monitor.py add <ip> <community> <oids...>
			""")
		sys.exit(1)
	elif len(sys.argv) == 1:
		job()

	elif "add" in sys.argv:
		ip, community = sys.argv[2], sys.argv[3]
		oids=[]
		for o in range(len(sys.argv)-4):
			oids.append(sys.argv[4+o])
		print(oids)
		add_device(ip, community, oids)


	ip, community, oid = sys.argv[1], sys.argv[2], sys.argv[3]
	get_snmp_data(ip, community, oid)


# get_snmp_data('192.168.1.1', 'public', '1.3.6.1.2.1.2.2.1.10.1')

