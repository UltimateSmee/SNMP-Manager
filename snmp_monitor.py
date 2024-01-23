import json
import schedule
import time
# time for scheduling? 
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
			ObjectType(ObjectIdentity(oid))
			))

		if errorIndication:
			print(f"Error Indication: {errorIndication}")
			return
		elif errorStatus:
			print(f"Error Status: {errorStatus}")
			return
		else:
			if not varBinds:
				print(f"No values returned for OID {oid}")
			else:
				for varBind in varBinds:
					# Cases where it returns nothing, format the output to be more readable
					if not varBind[1]:
						print(f"{str(varBind)[str(varBind).rfind('No Such'):]}: {varBind[0]} ( {str(varBind)[12:str(varBind).rfind('No Such')-2]} )")
					else:
						print(f"{varBind[0]} = {varBind[1]}")

		cursor.execute('''INSERT INTO snmp_data(ip_address, community, oid, value) VALUES(?, ?, ?, ?)''', (ip, community, oid, varBind[1].prettyPrint()))

	except Exception as e:
		# Common errors with error numbers will be displayed rather than the whole output
		t = str(e).rfind('[Errno')
		if t != -1:
			e = str(e)[t:]
		print(f"""
	#
	Error during SNMP query: 
	Device: {ip}
	Error: {str(e)}
	#
			""")

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
	if "run" in sys.argv:
		job()
		
	elif "add" in sys.argv:
		ip, community = sys.argv[2], sys.argv[3]
		oids=[]
		for o in range(len(sys.argv)-4):
			oids.append(sys.argv[4+o])
		add_device(ip, community, oids)
	
	elif len(sys.argv) == 4:
		ip, community, oid = sys.argv[1], sys.argv[2], sys.argv[3]
		get_snmp_data(ip, community, oid)

	else:
		print(f"""Usage:
			To run query on all devices in devices.json: python3 snmp_monitor.py 
			To run query on device: python3 snmp_monitor.py <ip> <community> <oid> 
			To add a new device: python3 snmp_monitor.py add <ip> <community> <oids...>
			""")
		sys.exit(1)

