from app.utils import utils

import pynvml

class PowerUtils(object):
    # Units are Wh

    # source for android phone using a Google Pixel 8 as an approximate reference:
    # https://www.reddit.com/r/batteries/comments/pathf6/does_anybody_know_howmany_watts_an_hour_it_takes/

    # source for the c3po reference:
    # https://www.wired.com/2012/05/how-big-is-c-3p0s-battery/

    references = {
        "phone": { "power": 17, "name": "Phones fully charged" }, 
        "lightbulb": { "power": 15, "name": "CFL light bulbs" },
        "c3po": { "power": 48.6, "name": "C3PO Droids" }
    }

    @classmethod
    def get_mean_power(cls, engine_id=None):
        # Returns mean power used by all the GPUs
        # at the moment the function is called
        # Units are Watts
        power = 0
        pynvml.nvmlInit()

        if engine_id:
            handle = pynvml.nvmlDeviceGetHandleByIndex(engine_id)
            power = (pynvml.nvmlDeviceGetPowerUsage(handle) / 1000)
        else:
            for i in range(0, pynvml.nvmlDeviceGetCount()):
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                power = power + (pynvml.nvmlDeviceGetPowerUsage(handle) / 1000)
            power = round(power / pynvml.nvmlDeviceGetCount())

        return power

    @classmethod
    def get_reference_text(cls, value, elapsed, reference=None):
        def generate_text(reference, value):
            ref_value = value / PowerUtils.references[reference]['power']
            ref_value = ref_value * (elapsed / 3600)
            ref_value = utils.parse_number(ref_value, round_number=2)
            return "{} {}".format(ref_value, PowerUtils.references[reference]['name'])

        if reference:
            if reference in PowerUtils.references:
                return generate_text(reference, value)
        else:
            texts = [generate_text(reference, value) for reference in PowerUtils.references]
            return texts