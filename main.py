import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import random
import math
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import csv

# Intentamos importar pandas para la exportación "Premium" a Excel
try:
  import pandas as pd
  HAS_PANDAS = True
except ImportError:
  HAS_PANDAS = False

# Configuración de estilo de gráficas para Modo Oscuro
plt.style.use('dark_background')

# --- PALETA DE COLORES (Modo Oscuro "Professional") ---
COLOR_BG = "#1e1e1e"        # Fondo oscuro
COLOR_PANEL = "#252526"     # Paneles
COLOR_TEXT = "#d4d4d4"      # Texto gris claro
COLOR_ACCENT = "#007acc"    # Azul intenso
COLOR_BTN = "#3c3c3c"       # Botones oscuros
COLOR_BTN_HOVER = "#505050" # Hover
COLOR_SUCCESS = "#4caf50"   # Verde éxito

# ---------------------------------------------------------
#  MOTOR DE SIMULACIÓN (M/M/s)
# ---------------------------------------------------------
def simulate_mm_s(lambda_rate, mu_rate, num_servers, num_clients, convert_to_mins=True):
  """
  Simula tráfico de red con modelo M/M/s.
  Retorna métricas, logs y datos para gráficas.
  """
  
  # Conversión de tasas
  if convert_to_mins:
    eff_lambda = lambda_rate / 60.0
    eff_mu = mu_rate / 60.0
  else:
    eff_lambda = lambda_rate
    eff_mu = mu_rate

  # Estado de los "Servidores Web"
  servers_end_time = [0.0] * num_servers
  current_arrival_time = 0.0
  detailed_data = []
  
  # Métricas
  wait_times = []
  system_times = []
  server_busy_durations = [0.0] * num_servers
  
  # Eventos para cálculo exacto de Lq (Buffer) y Ls
  events = [(0.0, 0)]

  for i in range(num_clients):
    # 1. Generar llegada (Poisson)
    r1 = random.random()
    if r1 >= 1.0: r1 = 0.999999
    interarrival = -math.log(1.0 - r1) / eff_lambda
    current_arrival_time += interarrival
    
    # 2. Generar servicio (Exponencial)
    r2 = random.random()
    if r2 >= 1.0: r2 = 0.999999
    service_dur = -math.log(1.0 - r2) / eff_mu
    
    # Evento: +1 Paquete en sistema
    events.append((current_arrival_time, 1))

    # 3. Asignar servidor (Load Balancing)
    earliest_server_idx = servers_end_time.index(min(servers_end_time))
    earliest_free_time = servers_end_time[earliest_server_idx]
    
    # 4. Calcular Latencias
    start_service = max(current_arrival_time, earliest_free_time)
    wait_time = max(0.0, start_service - current_arrival_time) # Latencia cola
    end_service = start_service + service_dur
    system_time = end_service - current_arrival_time # Latencia total
    
    server_idle = max(0.0, start_service - earliest_free_time)

    # Actualizar servidor
    servers_end_time[earliest_server_idx] = end_service
    server_busy_durations[earliest_server_idx] += service_dur
    
    # Evento: -1 Paquete (sale)
    events.append((end_service, -1))

    wait_times.append(wait_time)
    system_times.append(system_time)
    
    detailed_data.append({
      "id": i + 1,
      "interarrival": interarrival,
      "arrival": current_arrival_time,
      "server_id": earliest_server_idx + 1,
      "start_service": start_service,
      "wait": wait_time,
      "service_dur": service_dur,
      "end_service": end_service,
      "system_time": system_time,
      "server_idle": server_idle
    })

  # --- CÁLCULO DE ÁREAS (Integrales) para Lq y Ls exactos ---
  events.sort(key=lambda x: x[0])
  
  time_axis = []
  count_axis = [] 
  
  total_area_system = 0.0 
  total_area_queue = 0.0  
  
  current_count = 0
  last_time = 0.0
  
  for t, change in events:
    duration = t - last_time
    if duration > 0:
      total_area_system += current_count * duration
      queue_len = max(0, current_count - num_servers)
      total_area_queue += queue_len * duration
    
    # Puntos gráfica step
    time_axis.append(t)
    count_axis.append(current_count)
    
    current_count += change
    last_time = t
    
    time_axis.append(t)
    count_axis.append(current_count)

  total_sim_time = max(t for t, _ in events) if events else 1.0
  
  avg_ls = total_area_system / total_sim_time
  avg_lq = total_area_queue / total_sim_time
  
  server_utilization = []
  for busy in server_busy_durations:
    server_utilization.append((busy / total_sim_time) * 100)

  metrics = {
    "avg_wait": sum(wait_times) / len(wait_times) if wait_times else 0,
    "avg_system": sum(system_times) / len(system_times) if system_times else 0,
    "avg_ls": avg_ls,
    "avg_lq": avg_lq,
    "max_wait": max(wait_times) if wait_times else 0,
    "total_time": total_sim_time,
    "server_utilization": server_utilization
  }
  
  # Simplificar gráfica para matplotlib
  graph_t = []
  graph_c = []
  curr = 0
  for t, chg in events:
    graph_t.append(t)
    curr += chg
    graph_c.append(curr)

  return metrics, detailed_data, (graph_t, graph_c)

# ---------------------------------------------------------
#  INTERFAZ GRÁFICA (GUI)
# ---------------------------------------------------------
class QueueSimApp:
  def __init__(self, root):
    self.root = root
    self.root.title("Simulador de Tráfico de Red HTTP (Modelo M/M/s)")
    self.root.geometry("1400x900")
    self.root.minsize(1300, 700) # Evitar que se haga muy pequeña
    self.root.configure(bg=COLOR_BG)

    self.setup_styles()

    # Variables de entrada
    self.var_lambda = tk.StringVar(value="45")
    self.var_mu = tk.StringVar(value="60")
    self.var_servers = tk.StringVar(value="1")
    self.var_clients = tk.StringVar(value="50")
    self.var_mins = tk.BooleanVar(value=True)

    # --- 1. ENCABEZADO ---
    header_frame = tk.Frame(root, bg="#0e639c", bd=0, padx=20, pady=15)
    header_frame.pack(side=tk.TOP, fill=tk.X)
    
    lbl_title = tk.Label(header_frame, text="SIMULADOR DE BALANCEO DE CARGA HTTP", 
                          bg="#0e639c", fg="white", font=("Segoe UI", 16, "bold"))
    lbl_title.pack(anchor="w")
    
    desc_text = (
      "Simulación estocástica de distribución de paquetes HTTP hacia un clúster de servidores web.\n"
      "El sistema analiza métricas de QoS (Quality of Service) incluyendo latencia de red (Wq), "
      "ocupación de buffers (Lq) y throughput del servidor bajo el modelo matemático M/M/s."
    )
    lbl_desc = tk.Label(header_frame, text=desc_text,
                        bg="#0e639c", fg="#e0e0e0", font=("Segoe UI", 10), justify="left")
    lbl_desc.pack(anchor="w", pady=(5,0))

    # --- 2. PANEL DE CONTROL (Responsive) ---
    control_frame = ttk.Frame(root)
    control_frame.pack(side=tk.TOP, fill=tk.X, padx=15, pady=15)

    # Contenedor flexible para inputs
    inputs_frame = ttk.Frame(control_frame)
    inputs_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

    self.create_input(inputs_frame, "Tasa Peticiones (λ/hr):", self.var_lambda)
    self.create_input(inputs_frame, "Capacidad Nodo (μ/hr):", self.var_mu)
    self.create_input(inputs_frame, "Nodos/Servidores (s):", self.var_servers)
    self.create_input(inputs_frame, "Total Paquetes (n):", self.var_clients)

    # Checkbox Minutos
    cframe = ttk.Frame(inputs_frame)
    cframe.pack(side=tk.LEFT, padx=15)
    chk = tk.Checkbutton(cframe, text="Ver en Minutos", variable=self.var_mins, 
                          bg=COLOR_BG, fg="white", selectcolor=COLOR_PANEL, activebackground=COLOR_BG, font=("Arial", 9))
    chk.pack()

    # Botones
    btns_frame = ttk.Frame(control_frame)
    btns_frame.pack(side=tk.RIGHT)
    
    btn_run = ttk.Button(btns_frame, text="▶ INICIAR SIMULACIÓN", style="Success.TButton", command=self.run_simulation)
    btn_run.pack(side=tk.LEFT, padx=10)
    
    btn_exit = ttk.Button(btns_frame, text="SALIR", style="Danger.TButton", command=root.quit)
    btn_exit.pack(side=tk.LEFT, padx=10)

    # --- 3. PESTAÑAS (TABS) - RESPONSIVE ---
    self.notebook = ttk.Notebook(root)
    self.notebook.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)

    self.tab_dashboard = ttk.Frame(self.notebook, style="TFrame")
    self.notebook.add(self.tab_dashboard, text="  📈 DASHBOARD DE MÉTRICAS  ")

    self.tab_table = ttk.Frame(self.notebook, style="TFrame")
    self.notebook.add(self.tab_table, text="  📋 LOG DE TRÁFICO (TABLA)  ")

    self.setup_dashboard()
    self.setup_table()

  def setup_styles(self):
    s = ttk.Style()
    s.theme_use('clam')
    
    # General
    s.configure("TFrame", background=COLOR_BG)
    s.configure("TLabel", background=COLOR_BG, foreground=COLOR_TEXT, font=("Segoe UI", 10))
    
    # Botones
    s.configure("Success.TButton", background="#2e7d32", foreground="white", borderwidth=0, font=("Segoe UI", 10, "bold"))
    s.map("Success.TButton", background=[('active', "#4caf50")])
    s.configure("Danger.TButton", background="#c62828", foreground="white", borderwidth=0)
    s.map("Danger.TButton", background=[('active', "#e53935")])
    s.configure("Action.TButton", background="#007acc", foreground="white", borderwidth=0)
    s.map("Action.TButton", background=[('active', "#0098ff")])

    # Tabs
    s.configure("TNotebook", background=COLOR_BG, borderwidth=0)
    s.configure("TNotebook.Tab", background=COLOR_PANEL, foreground="gray", padding=[20, 10], font=("Segoe UI", 10, "bold"))
    s.map("TNotebook.Tab", background=[('selected', COLOR_ACCENT)], foreground=[('selected', 'white')])
    
    # Tabla
    s.configure("Treeview", background="#252526", foreground="white", fieldbackground="#252526", rowheight=30, borderwidth=0)
    s.configure("Treeview.Heading", background="#333333", foreground="white", relief="flat", font=("Segoe UI", 9, "bold"))
    s.map("Treeview.Heading", background=[('active', '#444444')])

  def create_input(self, parent, label, var):
    f = ttk.Frame(parent)
    f.pack(side=tk.LEFT, padx=8)
    ttk.Label(f, text=label, font=("Segoe UI", 9)).pack(side=tk.LEFT)
    e = tk.Entry(f, textvariable=var, width=8, bg="#3c3c3c", fg="white", insertbackground="white", bd=0, font=("Consolas", 11))
    e.pack(side=tk.LEFT, padx=5, ipady=3)

  def setup_dashboard(self):
    # Texto Reporte (Top)
    res_frame = ttk.Frame(self.tab_dashboard)
    res_frame.pack(side=tk.TOP, fill=tk.X, pady=10)
    
    self.text_results = tk.Text(res_frame, height=7, bg=COLOR_PANEL, fg="#4caf50", 
                                font=("Consolas", 12), bd=0, padx=15, pady=10)
    self.text_results.pack(fill=tk.BOTH, padx=5)

    # Área de Gráficas (Expansible)
    self.fig = plt.Figure(figsize=(8, 6), dpi=100)
    self.fig.patch.set_facecolor(COLOR_BG)
    
    self.ax1 = self.fig.add_subplot(211) 
    self.ax2 = self.fig.add_subplot(212) 
    self.fig.subplots_adjust(hspace=0.5, bottom=0.12, top=0.92, left=0.10, right=0.95)
    
    self.canvas = FigureCanvasTkAgg(self.fig, master=self.tab_dashboard)
    self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

  def setup_table(self):
    toolbar = ttk.Frame(self.tab_table)
    toolbar.pack(side=tk.TOP, fill=tk.X, pady=10, padx=10)
    
    btn_excel = ttk.Button(toolbar, text="📊 EXPORTAR A EXCEL (.xlsx)", style="Action.TButton", command=self.export_excel)
    btn_excel.pack(side=tk.RIGHT, padx=5)
    
    btn_csv = ttk.Button(toolbar, text="💾 CSV", style="Danger.TButton", command=self.export_csv)
    btn_csv.pack(side=tk.RIGHT, padx=5)

    # Tabla (Treeview)
    cols = ("ID", "Inter", "Llegada", "SrvID", "Inicio", "Espera", "Duracion", "Fin", "Sistema", "Ocio")
    self.tree = ttk.Treeview(self.tab_table, columns=cols, show='headings', selectmode="browse")
    
    headers = [
      "Paquete ID", "T. Entre Lleg.", "Hora Llegada", "Nodo Destino", 
      "Inicio Proceso", "Latencia (Cola)", "T. Proceso", 
      "Hora Salida", "Latencia Total", "Tiempo Ocio"
    ]
    
    for c, h in zip(cols, headers):
      self.tree.heading(c, text=h)
      self.tree.column(c, width=100, anchor="center")

    sb = ttk.Scrollbar(self.tab_table, orient=tk.VERTICAL, command=self.tree.yview)
    self.tree.configure(yscroll=sb.set)
    sb.pack(side=tk.RIGHT, fill=tk.Y)
    self.tree.pack(fill=tk.BOTH, expand=True)

  def run_simulation(self):
    try:
      lam = float(self.var_lambda.get())
      mu = float(self.var_mu.get())
      s = int(self.var_servers.get())
      n = int(self.var_clients.get())
      is_min = self.var_mins.get()
    except ValueError:
      messagebox.showerror("Error de Entrada", "Por favor ingrese parámetros numéricos válidos.")
      return

    metrics, data, graphs = simulate_mm_s(lam, mu, s, n, convert_to_mins=is_min)
    self.last_data = data
    self.last_unit = "min" if is_min else "hrs"
    
    unit = self.last_unit
    
    # 1. REPORTING - Corrección de Rho
    rho_val = sum(metrics['server_utilization']) / s # Promedio real
    status = "(SATURADO - CUELLO DE BOTELLA)" if rho_val >= 99 else "(ESTABLE)"
    
    txt = (f" REPORTE DE RENDIMIENTO DE RED ({n} Paquetes | {s} Nodos)\n"
            f" ------------------------------------------------------------\n"
            f" • Latencia Promedio en Cola (Wq):    {metrics['avg_wait']:.4f} {unit}\n"
            f" • Latencia Total en Sistema (Ws):    {metrics['avg_system']:.4f} {unit}\n"
            f" • Carga Promedio del Buffer (Lq):    {metrics['avg_lq']:.4f} paquetes\n"
            f" • Carga Promedio del Sistema (Ls):   {metrics['avg_ls']:.4f} paquetes\n"
            f" • Factor de Utilización (ρ):         {rho_val:.2f}% {status}")
    
    self.text_results.delete("1.0", tk.END)
    self.text_results.insert(tk.END, txt)

    # 2. TABLA
    for item in self.tree.get_children():
      self.tree.delete(item)
    
    for r in data:
      self.tree.insert("", tk.END, values=(
        r["id"],
        f"{r['interarrival']:.4f}",
        f"{r['arrival']:.4f}",
        f"Nodo-{r['server_id']}",
        f"{r['start_service']:.4f}",
        f"{r['wait']:.4f}",
        f"{r['service_dur']:.4f}",
        f"{r['end_service']:.4f}",
        f"{r['system_time']:.4f}",
        f"{r['server_idle']:.4f}"
      ))

    # 3. GRÁFICAS - Etiquetas de Ejes Detalladas
    t_ax, c_ax = graphs
    
    # Gráfica 1: Cola/Buffer
    self.ax1.clear()
    self.ax1.step(t_ax, c_ax, where='post', color='#00e5ff', linewidth=1.5)
    self.ax1.fill_between(t_ax, c_ax, step='post', alpha=0.15, color='#00e5ff')
    
    self.ax1.set_title(f"Evolución del Tráfico en Tiempo Real ({unit})", color="white", fontsize=10, fontweight='bold')
    self.ax1.set_xlabel(f"Tiempo de Simulación Transcurrido [{unit}]", color="#aaaaaa", fontsize=9)
    self.ax1.set_ylabel("Paquetes Activos", color="#aaaaaa", fontsize=9)
    self.ax1.grid(True, linestyle=':', alpha=0.3)

    # Gráfica 2: Carga de Nodos
    self.ax2.clear()
    labels = [f"Nodo {i+1}" for i in range(len(metrics["server_utilization"]))]
    vals = metrics["server_utilization"]
    colors = ['#66bb6a' if v < 80 else '#ff5252' for v in vals]
    
    self.ax2.bar(labels, vals, color=colors, alpha=0.8)
    self.ax2.set_title("Factor de Utilización por Nodo de Procesamiento", color="white", fontsize=10, fontweight='bold')
    self.ax2.set_xlabel("Identificador del Servidor Web", color="#aaaaaa", fontsize=9)
    self.ax2.set_ylabel("Porcentaje de uso de CPU (%)", color="#aaaaaa", fontsize=9)
    self.ax2.set_ylim(0, 105)
    
    for p, v in zip(self.ax2.patches, vals):
      self.ax2.annotate(f"{v:.1f}%", (p.get_x() + p.get_width() / 2., p.get_height()),
                        ha='center', va='bottom', color='white', fontsize=9)

    self.canvas.draw()
    messagebox.showinfo("Simulación Completada", "Análisis de tráfico generado correctamente.")

  def export_excel(self):
    """Exporta a Excel real (.xlsx) si pandas está instalado"""
    if not hasattr(self, 'last_data'):
      messagebox.showwarning("Alerta", "Primero debe ejecutar una simulación.")
      return

    if not HAS_PANDAS:
      messagebox.showerror("Librería Faltante", 
                            "No se detectó 'pandas' ni 'openpyxl'.\n\nPor favor instálelas:\n   pip install pandas openpyxl\n\nO use el botón 'CSV' como alternativa.")
      return

    filename = filedialog.asksaveasfilename(defaultextension=".xlsx", 
                                            filetypes=[("Excel Files", "*.xlsx")])
    if filename:
      try:
        df = pd.DataFrame(self.last_data)
        
        # Mapeo de nombres profesionales para el reporte
        col_map = {
          "id": "ID Paquete",
          "interarrival": f"T. Entre Llegadas ({self.last_unit})",
          "arrival": f"Hora Llegada ({self.last_unit})",
          "server_id": "Nodo Servidor",
          "start_service": f"Inicio Proceso ({self.last_unit})",
          "wait": f"Latencia Cola ({self.last_unit})",
          "service_dur": f"Tiempo Proceso ({self.last_unit})",
          "end_service": f"Hora Fin ({self.last_unit})",
          "system_time": f"Latencia Total ({self.last_unit})",
          "server_idle": f"Tiempo Ocio ({self.last_unit})"
        }
        df.rename(columns=col_map, inplace=True)
        
        df.to_excel(filename, index=False)
        messagebox.showinfo("Éxito", f"Reporte Excel generado:\n{filename}")
      except Exception as e:
        messagebox.showerror("Error de Exportación", f"Detalle del error:\n{e}")

  def export_csv(self):
    if not hasattr(self, 'last_data'): return
    fname = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
    if fname:
      with open(fname, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=self.last_data[0].keys())
        writer.writeheader()
        writer.writerows(self.last_data)
      messagebox.showinfo("Éxito", "Log CSV guardado.")

if __name__ == "__main__":
  root = tk.Tk()
  app = QueueSimApp(root)
  root.mainloop()