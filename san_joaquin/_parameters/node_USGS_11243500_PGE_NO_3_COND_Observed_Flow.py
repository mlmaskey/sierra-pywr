from parameters import WaterLPParameter

from utilities.converter import convert

class node_USGS_11243500_PGE_NO_3_COND_Observed_Flow(WaterLPParameter):
    """"""

    def _value(self, timestep, scenario_index):
        
        path="Gages/Streamflows/GaugeStreamFlow_cms_USJR.csv"
        data = self.read_csv(path)["11243500"]
        return data[timestep.datetime]
        
    def value(self, timestep, scenario_index):
        return convert(self._value(timestep, scenario_index), "m^3 s^-1", "m^3 day^-1", scale_in=1, scale_out=1000000.0)

    @classmethod
    def load(cls, model, data):
        return cls(model, **data)
        
node_USGS_11243500_PGE_NO_3_COND_Observed_Flow.register()
print(" [*] node_USGS_11243500_PGE_NO_3_COND_Observed_Flow successfully registered")
