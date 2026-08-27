"""
Copyright (c) 2021-, Haibin Wen, sunnypilot, and a number of other contributors.

This file is part of sunnypilot and is licensed under the MIT License.
See the LICENSE.md file in the root directory for more details.
"""
import json

from openpilot.common.swaglog import cloudlog
from openpilot.sunnypilot.selfdrive.car.sync_sunnylink_params import CAR_LIST_JSON_OUT

ONROAD_BRIGHTNESS_MIGRATION_VERSION: str = "1.0"
ONROAD_BRIGHTNESS_TIMER_MIGRATION_VERSION: str = "1.0"

# index → seconds mapping for OnroadScreenOffTimer (SSoT)
ONROAD_BRIGHTNESS_TIMER_VALUES = {0: 3, 1: 5, 2: 7, 3: 10, 4: 15, 5: 30, **{i: (i - 5) * 60 for i in range(6, 16)}}
VALID_TIMER_VALUES = set(ONROAD_BRIGHTNESS_TIMER_VALUES.values())


def _resolve_brand(_params) -> str:
  bundle = _params.get("CarPlatformBundle")
  if isinstance(bundle, dict) and bundle.get("brand"):
    return str(bundle["brand"])

  # Auto-fingerprinted cars have no bundle, fall back to the last known CarParams.
  CP_bytes = _params.get("CarParamsPersistent")
  if CP_bytes is None:
    return ""

  # Never raises: callers rely on "" to mean "brand unknown, skip the migration".
  try:
    from openpilot.cereal import messaging  # lazy: avoids heavy import at module level
    from opendbc.car.structs import car
    return str(messaging.log_from_bytes(CP_bytes, car.CarParams).brand)
  except Exception as e:
    cloudlog.exception(f"params_migration: failed to resolve brand from CarParamsPersistent: {e}")
    return ""


def _migrate_car_platform_bundle(_params):
  bundle = _params.get("CarPlatformBundle")
  if bundle is None:
    return

  old_platform = bundle.get("platform")
  if not old_platform:
    return

  from opendbc.car.fingerprints import MIGRATION  # lazy: avoids heavy import at module level
  if old_platform not in MIGRATION:
    return

  new_platform = str(MIGRATION[old_platform])

  with open(CAR_LIST_JSON_OUT) as f:
    car_list = json.load(f)

  candidates = [(k, v) for k, v in car_list.items() if v.get("platform") == new_platform]
  if candidates:
    old_model = bundle.get("model")
    key, data = next(((k, v) for k, v in candidates if v.get("model") == old_model), candidates[0])
    bundle = {**data, "name": key}
  else:
    bundle["platform"] = new_platform

  _params.put("CarPlatformBundle", bundle, block=True)
  cloudlog.info(f"params_migration: CarPlatformBundle migrated {old_platform!r} -> {new_platform!r}")


def _migrate_tesla_mads_screen_button(_params):
  # TeslaMadsScreenButton defaults to Off for fresh installs, but the screen button was previously always
  # active on Teslas with a vehicle bus. Seed existing Tesla installs with 3-finger to preserve that.
  try:
    if _params.get("TeslaMadsScreenButton") is not None:
      return

    if _resolve_brand(_params) != "tesla":
      return

    from opendbc.sunnypilot.car.tesla.values import MadsScreenButtonType  # lazy: avoids heavy import at module level
    _params.put("TeslaMadsScreenButton", MadsScreenButtonType.THREE_FINGER, block=True)
    cloudlog.info("params_migration: seeded TeslaMadsScreenButton with 3-finger to preserve existing behavior")
  except Exception as e:
    cloudlog.exception(f"Error migrating TeslaMadsScreenButton: {e}")


def _migrate_model_bundle_slots(_params):
  # Pre-split, a chestnut user's big-model selection lived in the single
  # ActiveBundle. Seed both slots; validation drops whichever does not match
  # its own manifest.
  try:
    if _params.get("ModelManager_ActiveBundleUSBGPU") is not None:
      return
    if (bundle := _params.get("ModelManager_ActiveBundle")) is None:
      return
    _params.put("ModelManager_ActiveBundleUSBGPU", bundle, block=True)
    cloudlog.info("params_migration: seeded ModelManager_ActiveBundleUSBGPU from ModelManager_ActiveBundle")
  except Exception as e:
    cloudlog.exception(f"Error migrating model bundle slots: {e}")


CRISPYGOAT_DEFAULTS_VERSION: str = "1"


def _seed_crispygoat_defaults(_params):
  # Seed recommended settings for a fresh install of sunnypilot4crispygoat on a
  # Hyundai/Kia/Genesis vehicle with a comma four. Runs once per fresh install;
  # the version flag survives normal restarts but a factory reset re-triggers it.
  try:
    if _params.get("CrispygoatDefaultsSeeded") == CRISPYGOAT_DEFAULTS_VERSION:
      return

    brand = _resolve_brand(_params)
    if not brand:
      # Car not fingerprinted yet; try again next boot.
      return
    if brand not in ("hyundai", "kia", "genesis"):
      # Brand is known and not HKG; mark done so we don't retry forever.
      _params.put("CrispygoatDefaultsSeeded", CRISPYGOAT_DEFAULTS_VERSION, block=True)
      return

    # MADS sub-toggles: PAUSE on brake (default is REMAIN_ACTIVE).
    _params.put("MadsSteeringMode", 1, block=True)
    # Independent lat/long engagement (default is unified).
    _params.put("MadsUnifiedEngagementMode", 0, block=True)
    # Auto Lane Change by Blinker: NUDGELESS (default is NUDGE).
    _params.put("AutoLaneChangeTimer", 1, block=True)
    # Lane change BSM delay (default off).
    _params.put("AutoLaneChangeBsmDelay", 1, block=True)
    # Custom Longitudinal Tuning: Predictive (default Off).
    _params.put("HyundaiLongitudinalTuning", 2, block=True)

    _params.put("CrispygoatDefaultsSeeded", CRISPYGOAT_DEFAULTS_VERSION, block=True)
    cloudlog.info("params_migration: seeded CrispygoatDefaultsV1 (MADS PAUSE, NUDGELESS, BSM delay, Predictive longitudinal)")
  except Exception as e:
    cloudlog.exception(f"Error seeding crispygoat defaults: {e}")


def run_migration(_params):
  # migrate OnroadScreenOffBrightness
  if _params.get("OnroadScreenOffBrightnessMigrated") != ONROAD_BRIGHTNESS_MIGRATION_VERSION:
    try:
      val = _params.get("OnroadScreenOffBrightness", return_default=True)
      if val >= 2:  # old: 5%, new: Screen Off
        new_val = val + 1
        _params.put("OnroadScreenOffBrightness", new_val, block=True)
        log_str = f"Successfully migrated OnroadScreenOffBrightness from {val} to {new_val}."
      else:
        log_str = "Migration not required for OnroadScreenOffBrightness."

      _params.put("OnroadScreenOffBrightnessMigrated", ONROAD_BRIGHTNESS_MIGRATION_VERSION, block=True)
      cloudlog.info(log_str + f" Setting OnroadScreenOffBrightnessMigrated to {ONROAD_BRIGHTNESS_MIGRATION_VERSION}")
    except Exception as e:
      cloudlog.exception(f"Error migrating OnroadScreenOffBrightness: {e}")

  # migrate OnroadScreenOffTimer
  if _params.get("OnroadScreenOffTimerMigrated") != ONROAD_BRIGHTNESS_TIMER_MIGRATION_VERSION:
    try:
      val = _params.get("OnroadScreenOffTimer", return_default=True)
      if val not in VALID_TIMER_VALUES:
        _params.put("OnroadScreenOffTimer", 15, block=True)
        log_str = f"Successfully migrated OnroadScreenOffTimer from {val} to 15 (default)."
      else:
        log_str = "Migration not required for OnroadScreenOffTimer."

      _params.put("OnroadScreenOffTimerMigrated", ONROAD_BRIGHTNESS_TIMER_MIGRATION_VERSION, block=True)
      cloudlog.info(log_str + f" Setting OnroadScreenOffTimerMigrated to {ONROAD_BRIGHTNESS_TIMER_MIGRATION_VERSION}")
    except Exception as e:
      cloudlog.exception(f"Error migrating OnroadScreenOffTimer: {e}")

  _migrate_car_platform_bundle(_params)

  # seed TeslaMadsScreenButton for existing Tesla installs
  _migrate_tesla_mads_screen_button(_params)

  # seed the usbgpu model slot from the pre-split single slot
  _migrate_model_bundle_slots(_params)

  # seed crispygoat fork defaults on fresh installs (HKG cars)
  _seed_crispygoat_defaults(_params)
