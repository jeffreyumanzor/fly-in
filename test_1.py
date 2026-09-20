from src.parser import Parser
from src.router import Scheduler
from src.models import Drone

graph, nb_drones = Parser(
    "maps/maps/challenger/01_the_impossible_dream.txt").parse()
if graph.start_hub:
    drones = [Drone(i, graph.start_hub) for i in range(1, nb_drones + 1)]

plans = Scheduler(graph, drones).build_plans()
for plan in plans:
    print(plan.drone.name, "llega en turno", plan.arrival_turn)
    for move in plan.moves:
        print("  turno", move.turn, "->", move.label)


"""
benchmarks:
"""
