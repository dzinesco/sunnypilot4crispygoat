"""
Copyright (c) 2021-, Haibin Wen, sunnypilot, and a number of other contributors.

This file is part of sunnypilot and is licensed under the MIT License.
See the LICENSE.md file in the root directory for more details.
"""
from openpilot.selfdrive.ui.mici.layouts.settings import settings as OP
from openpilot.selfdrive.ui.mici.layouts.settings.settings import SettingsBigButton
from openpilot.selfdrive.ui.mici.layouts.settings.device import DeviceLayoutMici
from openpilot.selfdrive.ui.mici.widgets.button import BigCircleButton
from openpilot.selfdrive.ui.mici.widgets.dialog import BigConfirmationDialog, BigDialog
from openpilot.selfdrive.ui.sunnypilot.mici.layouts.sunnylink import SunnylinkLayoutMici
from openpilot.selfdrive.ui.sunnypilot.mici.layouts.models import ModelsLayoutMici
from openpilot.selfdrive.ui.sunnypilot.layouts.settings.cruise import CruiseLayout
from openpilot.selfdrive.ui.sunnypilot.layouts.settings.steering import SteeringLayout
from openpilot.selfdrive.ui.sunnypilot.layouts.settings.vehicle import VehicleLayout
from openpilot.selfdrive.ui.sunnypilot.layouts.settings.visuals import VisualsLayout
from openpilot.selfdrive.ui.ui_state import ui_state
from openpilot.system.ui.lib.application import gui_app, FontWeight
from openpilot.system.ui.lib.multilang import tr

ICON_SIZE = 70
BIG_ICON_SIZE = 110


class SunnylinkBigButton(SettingsBigButton):
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self._label.set_font_weight(FontWeight.AUDIOWIDE)

  def _get_label_font_size(self):
    # Audiowide runs wider than Inter: "sunnylink" wraps to two lines at 64
    return 56


class SettingsLayoutSP(OP.SettingsLayout):
  def __init__(self):
    OP.SettingsLayout.__init__(self)

    device_panel = DeviceLayoutMici()
    self._scroller._items[2].set_click_callback(lambda: gui_app.push_widget(device_panel))

    self.icon_offroad_enable = gui_app.texture("../../sunnypilot/selfdrive/assets/icons_mici/always_offroad.png", BIG_ICON_SIZE,
                                               BIG_ICON_SIZE)
    self.icon_offroad_disable = gui_app.texture("../../sunnypilot/selfdrive/assets/icons_mici/disable_offroad.png", BIG_ICON_SIZE,
                                                BIG_ICON_SIZE)
    self.icon_offroad_slider = gui_app.texture("icons_mici/settings/device/lkas.png", BIG_ICON_SIZE, BIG_ICON_SIZE)

    sunnylink_panel = SunnylinkLayoutMici()
    sunnylink_btn = SunnylinkBigButton(tr("sunnylink"), "", gui_app.texture("../../sunnypilot/selfdrive/assets/icons_mici/sunnylink.png", 76, 44))
    sunnylink_btn.set_click_callback(lambda: gui_app.push_widget(sunnylink_panel))

    models_panel = ModelsLayoutMici()
    models_btn = SettingsBigButton(tr("models"), "", gui_app.texture("../../sunnypilot/selfdrive/assets/offroad/icon_models.png", ICON_SIZE, ICON_SIZE))
    models_btn.set_click_callback(lambda: gui_app.push_widget(models_panel))

    # Expose user-facing settings panels on comma four (no longer hidden behind sunnylink).
    # These push the full sunnypilot panel widgets, designed for the larger TIZI/TICI screen;
    # they may render slightly dense on mici but are fully functional.
    vehicle_panel = VehicleLayout()
    vehicle_btn = SettingsBigButton(tr("vehicle"), "", gui_app.texture("../../sunnypilot/selfdrive/assets/offroad/icon_vehicle.png", ICON_SIZE, ICON_SIZE))
    vehicle_btn.set_click_callback(lambda: gui_app.push_widget(vehicle_panel))

    cruise_panel = CruiseLayout()
    cruise_btn = SettingsBigButton(tr("cruise"), "", gui_app.texture("icons/speed_limit.png", ICON_SIZE, ICON_SIZE))
    cruise_btn.set_click_callback(lambda: gui_app.push_widget(cruise_panel))

    steering_panel = SteeringLayout()
    steering_btn = SettingsBigButton(tr("steering"), "", gui_app.texture("../../sunnypilot/selfdrive/assets/offroad/icon_lateral.png", ICON_SIZE, ICON_SIZE))
    steering_btn.set_click_callback(lambda: gui_app.push_widget(steering_panel))

    visuals_panel = VisualsLayout()
    visuals_btn = SettingsBigButton(tr("visuals"), "", gui_app.texture("../../sunnypilot/selfdrive/assets/offroad/icon_visuals.png", ICON_SIZE, ICON_SIZE))
    visuals_btn.set_click_callback(lambda: gui_app.push_widget(visuals_panel))

    # onroad: enable button sits at the front (left of toggles)
    self._enable_offroad_btn_onroad = BigCircleButton(self.icon_offroad_enable, red=True)
    self._enable_offroad_btn_onroad.set_click_callback(lambda: self._handle_always_offroad(True))
    self._enable_offroad_btn_onroad.set_visible(lambda: ui_state.started and not ui_state.always_offroad)

    # offroad: enable button sits at the end (right of developer)
    self._enable_offroad_btn_offroad = BigCircleButton(self.icon_offroad_enable, red=True)
    self._enable_offroad_btn_offroad.set_click_callback(lambda: self._handle_always_offroad(True))
    self._enable_offroad_btn_offroad.set_visible(lambda: not ui_state.started and not ui_state.always_offroad)

    self._disable_offroad_btn = BigCircleButton(self.icon_offroad_disable, red=False)
    self._disable_offroad_btn.set_click_callback(lambda: self._handle_always_offroad(False))
    self._disable_offroad_btn.set_visible(lambda: ui_state.always_offroad)

    items = self._scroller._items.copy()

    items.insert(1, models_btn)
    items.insert(5, sunnylink_btn)
    # crispygoat: expose user-facing panels on comma four (no longer hidden behind sunnylink).
    # These push the full sunnypilot panel widgets, designed for the larger TIZI/TICI screen;
    # they may render slightly dense on mici but are fully functional.
    # Each insert shifts later items, so we use positions that account for prior shifts.
    items.insert(6, vehicle_btn)
    items.insert(7, cruise_btn)
    items.insert(8, steering_btn)
    items.insert(9, visuals_btn)

    # front slots (only one ever visible at a time): exit-always-offroad, then enable-onroad
    items.insert(0, self._enable_offroad_btn_onroad)
    items.insert(0, self._disable_offroad_btn)
    # end slot: enable-offroad (right of developer)
    items.append(self._enable_offroad_btn_offroad)

    self._scroller._items.clear()
    for item in items:
      self._scroller.add_widget(item)

  def _update_state(self):
    super()._update_state()

  def _handle_always_offroad(self, enable: bool):

    def _set_offroad_status(status: bool):
      if not ui_state.engaged:
        ui_state.params.put_bool("OffroadMode", status)
        ui_state.always_offroad = status

    if not enable:
      dlg = BigConfirmationDialog(tr("slide to exit always offroad"), self.icon_offroad_slider, red=False,
                                  confirm_callback=lambda: _set_offroad_status(False))
    else:
      if ui_state.engaged:
        gui_app.push_widget(BigDialog(tr("disengage to enable always offroad"), "", ))
        return

      dlg = BigConfirmationDialog(tr("slide to force offroad"), self.icon_offroad_slider, red=True,
                                  confirm_callback=lambda: _set_offroad_status(True))
    gui_app.push_widget(dlg)
