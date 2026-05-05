import threading
import logging
from .engine import SimulationEngine

logger = logging.getLogger('simulations')

def run_simulation_async(simulation_id: str):
    """Run simulation in a background thread."""
    from .models import Simulation
    
    def _run():
        try:
            simulation = Simulation.objects.get(id=simulation_id)
            engine = SimulationEngine(simulation)
            engine.execute()
        except Exception as e:
            logger.error("Background simulation failed: %s", str(e), exc_info=True)
            try:
                from .models import Simulation
                sim = Simulation.objects.get(id=simulation_id)
                sim.status = 'failed'
                sim.error_message = str(e)
                sim.save()
            except Exception:
                pass
    
    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    logger.info("Simulation %s dispatched to background thread", simulation_id)