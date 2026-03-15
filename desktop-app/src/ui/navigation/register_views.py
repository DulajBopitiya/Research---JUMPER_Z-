# src/ui/navigation/register_views.py

from src.ui.navigation.view_registry import view_registry

from src.ui.views.dashboard_view import HomeFrame
from src.ui.views.simulations_view import SimulationFrame
from src.ui.views.code_editor_view import CodeEditorFrame
from src.ui.views.measurements_view import MeasurementsFrame
from src.ui.views.data_analysis_view import DataAnalysisFrame
from src.ui.views.notifications_view import NotificationsFrame
from src.ui.views.settings_view import SettingsFrame


def register_views():

    view_registry.register("Home", HomeFrame)
    view_registry.register("Simulation", SimulationFrame)
    view_registry.register("Code Editor", CodeEditorFrame)
    view_registry.register("Measurements", MeasurementsFrame)
    view_registry.register("Data & Analysis", DataAnalysisFrame)
    view_registry.register("Notifications", NotificationsFrame)
    view_registry.register("Settings", SettingsFrame)