import tkinter as tk
import random
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


# ---------------------------------------------------------
#  Modelo de simulación M/M/s para un servidor HTTP
# ---------------------------------------------------------
def simulate_mm_s(lambda_rate, mu_rate, num_servers, num_clients):
  # Tiempos
  arrival_times = []
  service_times = []

  # Generar llegadas exponenciales
  current_time = 0
  for _ in range(num_clients):
    interarrival = random.expovariate(lambda_rate)
    current_time += interarrival
    arrival_times.append(current_time)

  # Generar tiempos de servicio exponenciales
  service_times = [random.expovariate(mu_rate) for _ in range(num_clients)]

  # Estado de servidores y cola
  servers_free_at = [0.0] * num_servers  # tiempo en que cada servidor termina
  queue = []

  # Métricas
  wait_times = []
  system_times = []
  server_busy_time = [0.0] * num_servers
  server_idle_time = [0.0] * num_servers
  backlog_over_time = []

  for i in range(num_clients):
    arrival = arrival_times[i]
    service = service_times[i]

    # Actualizar backlog
    active = sum(1 for t in servers_free_at if t > arrival)
    backlog = max(0, active + len(queue))
    backlog_over_time.append((arrival, backlog))

    # Ver si hay servidor libre
    free_server = None
    for idx, t in enumerate(servers_free_at):
      if t <= arrival:
        free_server = idx
        break

    if free_server is not None:
      # El cliente entra directo a servicio
      start_service = arrival
      finish_service = start_service + service
      servers_free_at[free_server] = finish_service

      wait_times.append(0)
      system_times.append(service)
      server_busy_time[free_server] += service

    else:
      # Cliente entra a la cola
      queue.append((arrival, service))

      # Asignar cliente cuando el primer servidor se desocupe
      soonest = servers_free_at.index(min(servers_free_at))
      start_service = servers_free_at[soonest]
      wait = start_service - arrival

      service = queue.pop(0)[1]
      finish_service = start_service + service
      servers_free_at[soonest] = finish_service

      wait_times.append(wait)
      system_times.append(wait + service)
      server_busy_time[soonest] += service

  # Calcular ociosidad
  end_time = arrival_times[-1]
  for s in range(num_servers):
    server_idle_time[s] = max(0, end_time - server_busy_time[s])

  return {
    "wait_avg": sum(wait_times) / len(wait_times),
    "system_avg": sum(system_times) / len(system_times),
    "queue_avg": sum(b for _, b in backlog_over_time) / len(backlog_over_time),
    "busy": server_busy_time,
    "idle": server_idle_time,
    "backlog_over_time": backlog_over_time,
  }


# ---------------------------------------------------------
#  Interfaz gráfica (Tkinter + Matplotlib)
# ---------------------------------------------------------
class QueueApp:
  def __init__(self, root):
    self.root = root
    root.title("Simulación de Sistema de Colas HTTP (M/M/s)")

    # Parámetros
    frame = tk.Frame(root)
    frame.pack(padx=10, pady=10)

    tk.Label(frame, text="λ (llegadas por unidad de tiempo):").grid(row=0, column=0)
    tk.Label(frame, text="μ (servicio por unidad de tiempo):").grid(row=1, column=0)
    tk.Label(frame, text="Número de servidores (s):").grid(row=2, column=0)
    tk.Label(frame, text="Número de solicitudes:").grid(row=3, column=0)

    self.entry_lambda = tk.Entry(frame)
    self.entry_mu = tk.Entry(frame)
    self.entry_servers = tk.Entry(frame)
    self.entry_clients = tk.Entry(frame)

    self.entry_lambda.insert(0, "2")
    self.entry_mu.insert(0, "3")
    self.entry_servers.insert(0, "2")
    self.entry_clients.insert(0, "200")

    self.entry_lambda.grid(row=0, column=1)
    self.entry_mu.grid(row=1, column=1)
    self.entry_servers.grid(row=2, column=1)
    self.entry_clients.grid(row=3, column=1)

    tk.Button(frame, text="Simular", command=self.run_simulation).grid(row=4, column=0, columnspan=2, pady=10)

    # Área resultados
    self.results = tk.Text(root, height=12, width=80)
    self.results.pack(padx=10, pady=10)

    # Gráfica
    self.fig = plt.Figure(figsize=(6, 4))
    self.ax = self.fig.add_subplot(111)
    self.canvas = FigureCanvasTkAgg(self.fig, master=root)
    self.canvas.get_tk_widget().pack()

  def run_simulation(self):
    lam = float(self.entry_lambda.get())
    mu = float(self.entry_mu.get())
    servers = int(self.entry_servers.get())
    clients = int(self.entry_clients.get())

    out = simulate_mm_s(lam, mu, servers, clients)

    self.results.delete("1.0", tk.END)
    self.results.insert(tk.END, f"--- RESULTADOS ---\n")
    self.results.insert(tk.END, f"Tiempo promedio en cola: {out['wait_avg']:.4f}\n")
    self.results.insert(tk.END, f"Tiempo promedio en sistema: {out['system_avg']:.4f}\n")
    self.results.insert(tk.END, f"Longitud promedio de la cola: {out['queue_avg']:.4f}\n")
    self.results.insert(tk.END, f"\n--- Servidores ---\n")

    for i, (b, idle) in enumerate(zip(out["busy"], out["idle"])):
      self.results.insert(tk.END, f"Servidor {i+1}: Ocupado={b:.2f}, Ocio={idle:.2f}\n")

    # graficar backlog
    self.ax.clear()
    times = [t for t, b in out["backlog_over_time"]]
    backs = [b for t, b in out["backlog_over_time"]]
    self.ax.plot(times, backs)
    self.ax.set_title("Backlog del servidor HTTP")
    self.ax.set_xlabel("Tiempo")
    self.ax.set_ylabel("Tamaño de la cola")
    self.canvas.draw()


# ---------------------------------------------------------
#  Main
# ---------------------------------------------------------
if __name__ == "__main__":
  root = tk.Tk()
  app = QueueApp(root)
  root.mainloop()

