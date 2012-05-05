

from model import empire as empire_mdl
import model as mdl
from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.api import memcache
import calendar
import time
from datetime import datetime
import logging
import protobufs.warworlds_pb2 as pb


def getCached(keys, ProtoBuffClass):
  mc = memcache.Client()
  values = mc.get_multi(keys, for_cas=True)
  real_values = {}
  for key in values:
    real_value = ProtoBuffClass()
    real_value.ParseFromString(values[key])
    real_values[key] = real_value
  return real_values


def setCached(mapping):
  serialized_mapping = {}
  for key in mapping:
    serialized_mapping[key] = mapping[key].SerializeToString()

  mc = memcache.Client()
  mc.set_multi(serialized_mapping)


def clearCached(keys):
  mc = memcache.Client()
  mc.delete_multi(keys)


def deviceRegistrationPbToModel(model, pb):
  if pb.HasField('key'):
    model.key = pb.key
  model.deviceID = pb.device_id
  model.deviceRegistrationID = pb.device_registration_id
  model.deviceModel = pb.device_model
  model.deviceManufacturer = pb.device_manufacturer
  model.deviceBuild = pb.device_build
  model.deviceVersion = pb.device_version
  if pb.user:
    model.user = users.User(pb.user)

def deviceRegistrationModelToPb(pb, model):
  pb.key = str(model.key())
  pb.device_id = model.deviceID
  pb.device_registration_id = model.deviceRegistrationID
  pb.device_model = model.deviceModel
  pb.device_manufacturer = model.deviceManufacturer
  pb.device_build = model.deviceBuild
  pb.device_version = model.deviceVersion
  pb.user = model.user.email()


def empireModelToPb(empire_pb, empire_model):
  empire_pb.key = str(empire_model.key())
  empire_pb.display_name = empire_model.displayName
  empire_pb.user = empire_model.user.user_id()
  empire_pb.email = empire_model.user.email()
  empire_pb.state = empire_model.state


def empirePbToModel(empire_model, empire_pb):
  empire_model.displayName = empire_pb.display_name
  if empire_pb.HasField('email'):
    empire_model.user = users.User(empire_pb.email)
  empire_model.state = empire_pb.state


def colonyModelToPb(colony_pb, colony_model):
  colony_pb.key = str(colony_model.key())
  colony_pb.empire_key = str(empire_mdl.Colony.empire.get_value_for_datastore(colony_model))
  colony_pb.star_key = str(empire_mdl.Colony.star.get_value_for_datastore(colony_model))
  colony_pb.planet_key = str(empire_mdl.Colony.planet.get_value_for_datastore(colony_model))
  colony_pb.population = int(colony_model.population)
  colony_pb.last_simulation = int(dateTimeToEpoch(colony_model.lastSimulation))
  colony_pb.focus_population = colony_model.focusPopulation
  colony_pb.focus_farming = colony_model.focusFarming
  colony_pb.focus_mining = colony_model.focusMining
  colony_pb.focus_construction = colony_model.focusConstruction


def colonyPbToModel(colony_model, colony_pb):
  colony_model.population = float(colony_pb.population)
  colony_model.lastSimulation = epochToDateTime(colony_pb.last_simulation)
  colony_model.focusPopulation = colony_pb.focus_population
  colony_model.focusFarming = colony_pb.focus_farming
  colony_model.focusMining = colony_pb.focus_mining
  colony_model.focusConstruction = colony_pb.focus_construction


def sectorModelToPb(sector_pb, sector_model):
  sector_pb.x = sector_model.x
  sector_pb.y = sector_model.y
  if sector_model.numColonies:
    sector_pb.num_colonies = sector_model.numColonies
  else:
    sector_pb.num_colonies = 0

  for star_model in sector_model.stars:
    star_pb = sector_pb.stars.add()
    starModelToPb(star_pb, star_model)

  for colony_model in empire_mdl.Colony.getForSector(sector_model):
    colony_pb = sector_pb.colonies.add()
    colonyModelToPb(colony_pb, colony_model)


def starModelToPb(star_pb, star_model):
  star_pb.key = str(star_model.key())
  star_pb.sector_x = star_model.sector.x
  star_pb.sector_y = star_model.sector.y
  star_pb.offset_x = star_model.x
  star_pb.offset_y = star_model.y
  star_pb.name = star_model.name
  star_pb.colour = star_model.colour
  star_pb.classification = star_model.starTypeIndex
  star_pb.size = star_model.size
  if star_model.planets is not None:
    for planet_model in star_model.planets:
      planet_pb = star_pb.planets.add()
      planetModelToPb(planet_pb, planet_model)
    star_pb.num_planets = len(star_model.planets)


def empirePresenceModelToPb(presence_pb, presence_model):
  presence_pb.key = str(presence_model.key())
  presence_pb.empire_key = str(empire_mdl.EmpirePresence.empire.get_value_for_datastore(presence_model))
  presence_pb.star_key = str(empire_mdl.EmpirePresence.star.get_value_for_datastore(presence_model))
  presence_pb.total_goods = presence_model.totalGoods
  presence_pb.total_minerals = presence_model.totalMinerals


def empirePresencePbToModel(presence_model, presence_pb):
  presence_model.empire = db.Key(presence_pb.empire_key)
  presence_model.star = db.Key(presence_pb.star_key)
  presence_model.totalGoods = presence_pb.total_goods
  presence_model.totalMinerals = presence_pb.total_minerals


def planetModelToPb(planet_pb, planet_model):
  planet_pb.key = str(planet_model.key())
  planet_pb.index = planet_model.index
  planet_pb.planet_type = planet_model.planetTypeID + 1
  planet_pb.size = planet_model.size
  planet_pb.population_congeniality = planet_model.populationCongeniality
  planet_pb.farming_congeniality = planet_model.farmingCongeniality
  planet_pb.mining_congeniality = planet_model.miningCongeniality


def buildingModelToPb(building_pb, building_model):
  building_pb.key = str(building_model.key())
  building_pb.colony_key = str(empire_mdl.Building.colony.get_value_for_datastore(building_model))
  building_pb.design_name = building_model.designName


def buildRequestModelToPb(build_pb, build_model):
  build_pb.key = str(build_model.key())
  build_pb.colony_key = str(empire_mdl.BuildOperation.colony.get_value_for_datastore(build_model))
  build_pb.empire_key = str(empire_mdl.BuildOperation.empire.get_value_for_datastore(build_model))
  build_pb.design_name = build_model.designName
  build_pb.start_time = dateTimeToEpoch(build_model.startTime)
  build_pb.end_time = dateTimeToEpoch(build_model.endTime)
  build_pb.build_kind = build_model.designKind


def buildRequestPbToModel(build_model, build_pb):
  build_model.startTime = epochToDateTime(build_pb.start_time)
  build_model.endTime = epochToDateTime(build_pb.end_time)


def dateTimeToEpoch(dt):
  return calendar.timegm(dt.timetuple())


def epochToDateTime(epoch):
  return datetime.fromtimestamp(epoch)


def updateDeviceRegistration(registration_pb, user):
  registration_model = mdl.DeviceRegistration()
  deviceRegistrationPbToModel(registration_model, registration_pb)

  # ignore what they said in the PB, we'll set the user to their own user anyway
  registration_model.user = user
  registration_model.put()

  deviceRegistrationModelToPb(registration_pb, registration_model)
  clearCached(['devices:for-user:%s' % (user.user_id())])
  return registration_pb

def getDevicesForUser(user_email):
  cache_key = 'devices:for-user:%s' % (user_email)
  logging.debug("Cache key: %s" % (cache_key))
  devices = getCached([cache_key], pb.DeviceRegistrations)
  if cache_key in devices:
    return devices[cache_key]

  devices_mdl = mdl.DeviceRegistration.getByUser(users.User(user_email))
  devices_pb = pb.DeviceRegistrations()
  for device_mdl in devices_mdl:
    device_pb = devices_pb.registrations.add()
    deviceRegistrationModelToPb(device_pb, device_mdl)

  setCached({cache_key: devices_pb})
  return devices_pb
