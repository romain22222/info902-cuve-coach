import sys
from enum import Enum
from typing import List

import mysql.connector

conn = mysql.connector.connect(
	host="localhost",
	user="root",
	password="AZERTYuiop@123456789",
	database="mysql"
)

# conn = mysql.connector.connect(
# 	host="localhost",
# 	user="root",
# 	password="admin",
# 	database="mysql"
# )

cursor = conn.cursor()


def doCommand(command: str):
	cursor.execute(command)
	return cursor.fetchall()


"""
Database structure:
Table fields {
	id integer [primary key]
	current_plant integer
	saved_prog integer [note: "1: each X hours, 2: aiming humidity X kPa"]
	saved_number integer
	linked_pump integer
}

Table plants {
	id integer [primary key]
	name text
	min_time_aim integer
	max_time_aim integer
	min_humidity integer
	max_humidity integer
}

Table users {
	id integer [primary key]
	username text
	pass text
}

Table plant_managment {
	user_id integer
	plant_id integer
	success_setup integer
	failed_setup integer
}


Ref: users.id < plant_managment.user_id
Ref: plants.id < fields.current_plant
Ref: plants.id < plant_managment.plant_id

"""


def init(fullReload: bool):
	if fullReload:
		doCommand("DROP DATABASE IF EXISTS cuveio")

		doCommand("CREATE DATABASE cuveio")
		doCommand("USE cuveio")
		doCommand(
			"CREATE TABLE IF NOT EXISTS fields (id INTEGER PRIMARY KEY AUTO_INCREMENT, current_plant INTEGER, saved_prog INTEGER, saved_number INTEGER, linked_pump INTEGER)")
		doCommand(
			"CREATE TABLE IF NOT EXISTS plants (id INTEGER PRIMARY KEY AUTO_INCREMENT, name TEXT, min_time_aim INTEGER, max_time_aim INTEGER, min_humidity INTEGER, max_humidity INTEGER)")
		doCommand("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTO_INCREMENT, username TEXT, pass TEXT)")
		doCommand(
			"CREATE TABLE IF NOT EXISTS plant_managment (user_id INTEGER, plant_id INTEGER, success_setup INTEGER, failed_setup INTEGER)")
		# Create 3 users with names "Romain", "Irilind" and "Kylian"
		doCommand("INSERT INTO users (username, pass) VALUES ('Romain', '0683207903f1832a87e488645fe0761354701afd028a2d7fadb8131bb8f96a67')")
		doCommand("INSERT INTO users (username, pass) VALUES ('Irilind', '7b4a90e5f9a0f7e3e3d3bae61e0f3d9b3e3d3bae61e0f3d9b87e488645fe3547')")
		doCommand("INSERT INTO users (username, pass) VALUES ('Kylian', 'd3bae61e0f37545d9b87e488645fe3547b4a90e5f9a0f7e3e3d3bae61e0f3d9b')")
		# Create 5 plants with names "Tomato", "Potato", "Cactus", "Rose" and "Sunflower"
		doCommand("INSERT INTO plants (name, min_time_aim, max_time_aim, min_humidity, max_humidity) VALUES ('Tomato', 6, 8, 30, 40)")
		doCommand("INSERT INTO plants (name, min_time_aim, max_time_aim, min_humidity, max_humidity) VALUES ('Potato', 8, 10, 25, 35)")
		doCommand("INSERT INTO plants (name, min_time_aim, max_time_aim, min_humidity, max_humidity) VALUES ('Cactus', 48, 72, 10, 20)")
		doCommand("INSERT INTO plants (name, min_time_aim, max_time_aim, min_humidity, max_humidity) VALUES ('Rose', 8, 12, 40, 50)")
		doCommand("INSERT INTO plants (name, min_time_aim, max_time_aim, min_humidity, max_humidity) VALUES ('Sunflower', 12, 16, 20, 30)")
		# Create 4 empty fields
		# doCommand("INSERT INTO fields (current_plant, saved_prog, saved_number, linked_pump) VALUES (1, 1, 6, 0)")
		doCommand("INSERT INTO fields (current_plant, saved_prog, saved_number, linked_pump) VALUES (NULL, NULL, NULL, 0)")
		doCommand("INSERT INTO fields (current_plant, saved_prog, saved_number, linked_pump) VALUES (NULL, NULL, NULL, 1)")
		doCommand("INSERT INTO fields (current_plant, saved_prog, saved_number, linked_pump) VALUES (NULL, NULL, NULL, 2)")
		doCommand("INSERT INTO fields (current_plant, saved_prog, saved_number, linked_pump) VALUES (NULL, NULL, NULL, 3)")

		nbU = doCommand("SELECT COUNT(*) FROM users")[0][0]
		nbP = doCommand("SELECT COUNT(*) FROM plants")[0][0]
		# Create a plant managment for each pair of user / plant
		for i in range(nbU):
			for j in range(nbP):
				doCommand(f"INSERT INTO plant_managment(user_id, plant_id, success_setup, failed_setup) VALUES ({i+1}, {j+1}, 0, 0)")
		doCommand(f"UPDATE plant_managment SET success_setup = 9 WHERE user_id = 1 AND plant_id = 1")
		conn.commit()
	else:
		doCommand("USE cuveio")


class Program(Enum):
	HOUR = 1
	HUMIDITY = 2


class Plant:
	def __init__(self, plant_id: int, name: str, min_time_aim: int, max_time_aim: int,
				min_humidity: int, max_humidity: int):
		self.id: int = plant_id
		self.name: str = name
		self.min_time_aim: int = min_time_aim
		self.max_time_aim: int = max_time_aim
		self.min_humidity: int = min_humidity
		self.max_humidity: int = max_humidity

	@classmethod
	def findById(cls, plant_id: int) -> 'Plant':
		values = doCommand(f"SELECT * FROM plants WHERE id = {plant_id if plant_id is not None else 'NULL'}")
		return cls(*values[0]) if len(values) > 0 else None

	@classmethod
	def getAllPlants(cls):
		values = doCommand("SELECT * FROM plants")
		return [cls(*v) for v in values]


class Field:
	def __init__(self, field_id: int, current_plant: int, saved_prog: int, saved_number: int, linked_pump: int):
		self.id: int = field_id
		self.current_plant: Plant = Plant.findById(current_plant)
		self.saved_prog: Program = Program(saved_prog-1) if saved_prog is not None else None
		self.saved_number: int = saved_number
		self.linked_pump: int = linked_pump

	@classmethod
	def findById(cls, field_id: int) -> 'Field':
		values = doCommand(f"SELECT * FROM fields WHERE id = {field_id if field_id is not None else 'NULL'}")
		return cls(*values[0]) if len(values) > 0 else None

	@classmethod
	def getAllFields(cls) -> List['Field']:
		values = doCommand("SELECT * FROM fields")
		return [cls(*v) for v in values]

	def save(self):
		doCommand(f"UPDATE fields SET current_plant = {self.current_plant.id if self.current_plant is not None else 'NULL'}, saved_prog = {1 if self.saved_prog.value == Program.HOUR else 2}, saved_number = {self.saved_number}, linked_pump = {self.linked_pump} WHERE id = {self.id if id is not None else 'NULL'}")
		conn.commit()

	@classmethod
	def findByLinkedPump(cls, linked_pump: int) -> 'Field':
		print(f"SELECT * FROM fields WHERE linked_pump = {linked_pump if linked_pump is not None else 'NULL'}")
		values = doCommand(f"SELECT * FROM fields WHERE linked_pump = {linked_pump if linked_pump is not None else 'NULL'}")
		print(f"good for {linked_pump} : {values}")
		return cls(*values[0]) if len(values) > 0 else None


class User:
	def __init__(self, user_id: int, username: str, password: str):
		self.id: int = user_id
		self.username: str = username
		self.password: str = password

	@classmethod
	def findById(cls, user_id: int) -> 'User':
		values = doCommand(f"SELECT * FROM users WHERE id = {user_id if user_id is not None else 'NULL'}")
		return cls(*values[0]) if len(values) > 0 else None


class PlantManagment:
	def __init__(self, user_id: int, plant_id: int, success_setup: int, failed_setup: int):
		self.user: User = User.findById(user_id)
		self.plant: Plant = Plant.findById(plant_id)
		self.success_setup: int = success_setup
		self.failed_setup: int = failed_setup

	@classmethod
	def findByUserAndPlant(cls, user_id: int, plant_id: int) -> 'PlantManagment':
		values = doCommand(f"SELECT * FROM plant_managment WHERE user_id = {user_id} AND plant_id = {plant_id if plant_id is not None else 'NULL'}")
		return cls(*values[0]) if len(values) > 0 else None

	@classmethod
	def findPlantsOfUser(cls, user_id: int) -> List['PlantManagment']:
		values = doCommand(f"SELECT * FROM plant_managment WHERE user_id = {user_id if user_id is not None else 'NULL'}")
		return [cls(*v) for v in values]

	def getSetupRatio(self) -> float:
		return 0 if self.getSetupTimes() == 0 else self.success_setup / self.getSetupTimes()

	def getSetupTimes(self) -> int:
		return self.success_setup + self.failed_setup

	def save(self):
		doCommand(f"UPDATE plant_managment SET success_setup = {self.success_setup}, failed_setup = {self.failed_setup} WHERE user_id = {self.user.id} AND plant_id = {self.plant.id if id is not None else 'NULL'}")
		conn.commit()


init("reload" in sys.argv)
