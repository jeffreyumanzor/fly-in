from src.parser import Parser
from src.models import Drone
from src.router import Scheduler
from src.simulation import SimulationEngine

graph, nb_drones = Parser("maps/maps/challenger/01_the_impossible_dream.txt").parse()
drones = [Drone(i, graph.start_hub) for i in range(1, nb_drones + 1)]

plans = Scheduler(graph, drones).build_plans()
result = SimulationEngine(graph, drones, plans).run()

for turn_tokens in result.turns:
    print(" ".join(turn_tokens))
print("Total turns:", result.total_turns)
