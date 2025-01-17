from watttime.api import WattTimeOptimizer, WattTimeForecast, WattTimeHistorical
import pandas as pd
import math
from utils import convert_to_utc, get_timezone_from_dict
import numpy as np
from typing import Optional

class ImpactEvaluator:
    def __init__(self, username:str, password:str, obj: pd.DataFrame, region:Optional[str] = None):
        """
        Evaluates the impact of a charging schedule.

        Parameters:
        -----------
        username : str
            API username
        password : str
            API password
        obj: pd.DataFrame
            Watttime Optimizer results frame.
        """
        self.actuals = WattTimeHistorical(username,password)
        self.obj = obj

    def get_historical_actual_data(self, region = None):
        """
        Retrieve historical actual data for a specific plug-in time, horizon, and region.

        Parameters:
        -----------
        region : str
            The region for which to retrieve the actual data.
        
        Returns:
        --------
        pd.DataFrame
            A DataFrame containing historical actual data.
        """

        if region is None:
            region = self.region

        session_start_time = self.obj.index[0]
        session_end_time = self.obj.index[-1]

        return self.actuals.get_historical_pandas(
            start=session_start_time,
            end=session_end_time,
            region=region,
        )

    def get_charging_schedule(self):
        """
        Extract and flatten usage values from input data
        Args:
            x: Input dictionary containing 'usage' key
        Returns:
            Flattened array of usage values
        """
        return self.obj["usage"].values.flatten()
    
    def get_energy_usage(self):
        """
        Extract and flatten usage values from input data
        Args:
            x: Input dictionary containing 'usage' key
        Returns:
            Flattened array of usage values
        """
        return self.obj["energy_usage_mwh"].values.flatten()

    def get_actual_emissions(self,region):
        """
        Calculate total CO2 emissions in pounds
        Args:
            region: eGrid region for API
        Returns:
            Sum of CO2 emissions
        """
        moer = self.get_historical_actual_data(region)
        energy_usage_mwh = np.array(self.obj.energy_usage_mwh).flatten()
        
        return np.dot(moer[: energy_usage_mwh.shape[0]], energy_usage_mwh).sum()

    def get_forecast_emissions(self):
        """
        Calculate total CO2 emissions in pounds
        Args:
            x: Input dictionary containing 'emissions_co2e_lb' key
        Returns:
            Sum of CO2 emissions
        """
        return self.obj["emissions_co2e_lb"].sum()

class OptChargeEvaluator(WattTimeOptimizer):
    def __init__(self, username: str, password: str):
        """
        Initialize OptimalCharger with API credentials.
        
        Parameters:
        -----------
        username : str
            API username
        password : str
            API password
        """
        self.username = username
        self.password = password
        self.optimizer = WattTimeOptimizer(username, password)
        self.forecast_history = WattTimeForecast(username,password)

    def get_historical_fcst_data(self, session_start_time, horizon, region):
        """
        Retrieve historical forecast data for a specific plug-in time, horizon, and region.

        Parameters:
        -----------
        session_start_time : datetime
            The time at which the EV was plugged in.
        horizon : int
            The number of hours to forecast ahead.
        region : str
            The region for which to retrieve the forecast data.

        Returns:
        --------
        pd.DataFrame
            A DataFrame containing historical forecast data.
        """

        time_zone = get_timezone_from_dict(region)
        session_start_time = pd.Timestamp(convert_to_utc(session_start_time, time_zone))
        horizon = math.ceil(horizon / 12)

        return self.forecast_history.get_historical_forecast_pandas(
            start=session_start_time - pd.Timedelta(minutes=5),
            end=session_start_time,
            horizon_hours=horizon,
            region=region,
        )
    
    def get_schedule_and_cost_api(
        self,
        usage_power_kw: float,
        time_needed: float,
        total_time_horizon: int,
        moer_data: pd.DataFrame,
        optimization_method: str = "auto",
        charge_per_interval: list = []
    ) -> pd.DataFrame:
        """
        Generate optimal charging schedule based on MOER forecasts.
        
        Parameters:
        -----------
        usage_power_kw : float
            Power usage in kilowatts
        time_needed : float
            Required charging time in minutes
        total_time_horizon : int
            Total scheduling horizon in intervals
        moer_data : pd.DataFrame
            MOER forecast data
        optimization_method : str, optional
            Optimization method (default: "auto")
        charge_per_interval : list, optional
            List of charging constraints per interval
            
        Returns:
        --------
        pd.DataFrame
            Optimal charging schedule with emissions data
        """
        # Get time window from MOER data
        usage_window_start = pd.to_datetime(moer_data["point_time"].iloc[0])
        usage_window_end = pd.to_datetime(
            moer_data["point_time"].iloc[total_time_horizon - 1]
        )
        
        # Adjust time needed if it exceeds available window
        time_needed = min(
            time_needed, 
            total_time_horizon * self.optimizer.OPT_INTERVAL
        )
        
        # Generate optimal usage plan
        schedule = self.optimizer.get_optimal_usage_plan(
            region=None,
            usage_window_start=usage_window_start,
            usage_window_end=usage_window_end,
            usage_time_required_minutes=time_needed,
            usage_power_kw=usage_power_kw,
            optimization_method=optimization_method,
            moer_data_override=moer_data,
            charge_per_interval=charge_per_interval
        )
        
        # Validate emissions data
        if schedule["emissions_co2e_lb"].sum() == 0.0:
            self._log_zero_emissions_warning(
                usage_power_kw,
                time_needed,
                schedule["usage"].sum()
            )
            
        return schedule
            
    def _log_zero_emissions_warning(
        self,
        power: float,
        time_needed: float,
        total_usage: float
    ) -> None:
        """Log warning when zero emissions are detected."""
        print(
            "Warning using 0.0 lb of CO2e:",
            power,
            time_needed,
            total_usage
        )