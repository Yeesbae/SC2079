# Autonomous Maze Solver and Path Visualizer

This project implements an autonomous path-finding system designed to navigate a robot through an arena to visit multiple obstacles in the most efficient order. It combines **A* Search** for local point-to-point navigation and **Dynamic Programming (TSP)** for global order optimization.

---

## 1. Execution Instructions

To run the simulation and visualize the path-finding logic:

1.  Open your terminal in the project root directory.
2.  Execute the main entry point:
    ```bash
    python main.py
    ```
3.  **Process Flow**: 
    * The script initializes `MazeSolver` with defined arena dimensions.
    * It calls `get_optimal_order_dp()`, which calculates the shortest Hamiltonian path to visit all obstacle view-states.
    * The `MazeVisualizer` then initializes a Pygame interface to render the results.

---

## 2. MazeVisualizer UI Controls (Pygame)

The visualizer is set to a **Paused** state by default. Use the following keys to interact with the simulation:

| Key | Action |
| :--- | :--- |
| **G** | **Autoplay**: The robot automatically follows the computed path from its current index. |
| **SPACE** | **Pause/Unpause**: Toggles the autoplay state during execution. |
| **R** | **Reset**: Resets the robot to the starting position and clears the animation state. |
| **RIGHT** | **Manual Forward**: Move the robot one step forward to the next state in the path. |
| **LEFT** | **Manual Rewind**: Move the robot one step backward to the previous state. |
| **+ / =** | **Speed Up**: Increases the animation speed (reduces frames per move). |
| **- / _** | **Slow Down**: Decreases the animation speed (increases frames per move). |

---

## 3. Algorithm Architecture

The `MazeSolver` utilizes a multi-stage pipeline to transform raw obstacle coordinates into a sequence of executable robot commands.

### A. State Space and View Generation
For every obstacle, the system determines a set of valid **View States**. These are specific $(x, y, \theta)$ coordinates where the robot's camera is perfectly aligned with the obstacle face. 



### B. A* Path Precomputation
The algorithm utilizes the **A* Search Algorithm** to find the shortest path between all pairs of relevant states.
* **Cost Function**: $f(n) = g(n) + h(n)$
* **$g(n)$**: The path cost from the origin, including distance and $TURN\_FACTOR$ penalties.
* **$h(n)$**: The heuristic (Manhattan distance) to the destination.

### C. Traveling Salesperson Problem (TSP) Optimization
To visit $N$ obstacles efficiently, the solver builds an **Obstacle-Level Distance Matrix**.
1.  The cost between Obstacle $i$ and Obstacle $j$ is calculated as the minimum A* cost between any of their respective view states.
2.  The `solve_tsp_dynamic_programming` function finds the optimal permutation of obstacles to minimize total travel distance.

### D. Kinematic Constraints and Safety Masks
The solver ensures the path is physically executable by the robot:
* **Hardcoded Turns**: Movement is restricted to straight lines and 90-degree curves based on the $x\_change$ and $y\_change$ of the robot's turning radius.
* **Safety Sweeps**: The `is_turn_sweep_safe` function utilizes a `NORTH_LEFT_MASK` to verify that the entire arc of a turn is clear of obstacles, preventing the robot's chassis from clipping corners.



### E. Mathematical Objective
The global objective is to minimize the total cost $C_{total}$:
$$C_{total} = \sum_{i=1}^{n} \text{Path}(State_{i-1}, State_{i}) + \sum_{i=1}^{n} Penalty_{i}$$
Where $Penalty$ accounts for orientation changes and specific view-state difficulties.

---