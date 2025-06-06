import tkinter as tk
from tkinter import filedialog, scrolledtext, ttk
import threading # Per eseguire l'analisi in un thread separato
from pathlib import Path

# Importa la funzione principale e, se necessario, altre utility dal tuo script originale
from gestore_duplicati_musicali import avvia_gestione_duplicati, _default_logger # Usiamo _default_logger come fallback

class AppGestoreMusicaleV0_1:
    def __init__(self, root_window):
        self.root = root_window
        self.root.title("Gestore Duplicati Musicali v0.1 Alpha")
        self.root.geometry("800x600")

        # Variabili per i percorsi delle cartelle
        self.cartella_musicale_var = tk.StringVar()
        self.cartella_duplicati_var = tk.StringVar()
        self.cartella_non_conformi_var = tk.StringVar()
        self.cartella_da_verificare_var = tk.StringVar() # Variabile per il percorso DA VERIFICARE

        # Frame principale
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        # ---- Sezione Selezione Cartelle ----
        cartelle_frame = ttk.LabelFrame(main_frame, text="Percorsi Cartelle", padding="10")
        cartelle_frame.grid(row=0, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        cartelle_frame.columnconfigure(1, weight=1)

        ttk.Label(cartelle_frame, text="Cartella Musicale:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Entry(cartelle_frame, textvariable=self.cartella_musicale_var, width=70).grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5, pady=2)
        ttk.Button(cartelle_frame, text="Sfoglia...", command=lambda: self.seleziona_cartella(self.cartella_musicale_var, "Seleziona Cartella Musicale")).grid(row=0, column=2, sticky=tk.E, padx=5, pady=2)

        ttk.Label(cartelle_frame, text="Cartella Duplicati:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Entry(cartelle_frame, textvariable=self.cartella_duplicati_var, width=70).grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5, pady=2)
        ttk.Button(cartelle_frame, text="Sfoglia...", command=lambda: self.seleziona_cartella(self.cartella_duplicati_var, "Seleziona Cartella per i Duplicati", True)).grid(row=1, column=2, sticky=tk.E, padx=5, pady=2)

        ttk.Label(cartelle_frame, text="Cartella Non Conformi:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Entry(cartelle_frame, textvariable=self.cartella_non_conformi_var, width=70).grid(row=2, column=1, sticky=(tk.W, tk.E), padx=5, pady=2)
        ttk.Button(cartelle_frame, text="Sfoglia...", command=lambda: self.seleziona_cartella(self.cartella_non_conformi_var, "Seleziona Cartella per i Non Conformi", True)).grid(row=2, column=2, sticky=tk.E, padx=5, pady=2)

        # Aggiungiamo un campo (disabilitato) per mostrare il percorso "DA VERIFICARE"
        ttk.Label(cartelle_frame, text="Cartella 'Da Verificare':").grid(row=3, column=0, sticky=tk.W, padx=5, pady=2)
        self.entry_da_verificare = ttk.Entry(cartelle_frame, textvariable=self.cartella_da_verificare_var, width=70, state='readonly')
        self.entry_da_verificare.grid(row=3, column=1, sticky=(tk.W, tk.E), padx=5, pady=2)
        # Non mettiamo un bottone Sfoglia, dato che è derivato

        # ---- Area di Log ----
        log_frame = ttk.LabelFrame(main_frame, text="Log Operazioni", padding="10")
        log_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        main_frame.rowconfigure(1, weight=1) # Permette al log frame di espandersi
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self.log_area = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=15, state=tk.DISABLED)
        self.log_area.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # ---- Pulsanti Azione ----
        action_frame = ttk.Frame(main_frame, padding="10")
        action_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        action_frame.columnconfigure(0, weight=1) # Fa sì che il pulsante di avvio sia a sinistra
        action_frame.columnconfigure(1, weight=0)
        action_frame.columnconfigure(2, weight=0)


        self.avvia_button = ttk.Button(action_frame, text="Avvia Analisi", command=self.avvia_analisi_thread)
        self.avvia_button.grid(row=0, column=0, sticky=tk.W, padx=5)

        self.pulisci_log_button = ttk.Button(action_frame, text="Pulisci Log", command=self.pulisci_log)
        self.pulisci_log_button.grid(row=0, column=1, sticky=tk.E, padx=5)

        self.stop_button = ttk.Button(action_frame, text="Interrompi (Non Impl.)", state=tk.DISABLED)
        self.stop_button.grid(row=0, column=2, sticky=tk.E, padx=5)
        
        # ---- Barra di Progresso ----
        self.progress_bar = ttk.Progressbar(main_frame, orient=tk.HORIZONTAL, length=300, mode='determinate')
        self.progress_bar.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10, padx=5)

    def seleziona_cartella(self, var_percorso, titolo_dialog, ask_save_dir=False):
        """ Apre una finestra di dialogo per selezionare una cartella. """
        percorso_selezionato = filedialog.askdirectory(title=titolo_dialog)
        if percorso_selezionato:
            var_percorso.set(percorso_selezionato)
            # Imposta default per duplicati/non conformi se non ancora specificati e se stiamo selezionando la cartella musicale
            if var_percorso == self.cartella_musicale_var: 
                path_musicale_sel = Path(percorso_selezionato)
                if not self.cartella_duplicati_var.get():
                    path_duplicati_default = path_musicale_sel / "DOPPIONI"
                    self.cartella_duplicati_var.set(str(path_duplicati_default))
                    # Imposta anche il default per DA_VERIFICARE basato sui duplicati
                    self.cartella_da_verificare_var.set(str(path_duplicati_default / "DA_VERIFICARE")) 
                if not self.cartella_non_conformi_var.get():
                    self.cartella_non_conformi_var.set(str(path_musicale_sel / "NON CONFORMI"))
            
            # Se l'utente cambia la cartella duplicati, aggiorna quella DA VERIFICARE
            elif var_percorso == self.cartella_duplicati_var:
                if self.cartella_duplicati_var.get():
                    self.cartella_da_verificare_var.set(str(Path(self.cartella_duplicati_var.get()) / "DA_VERIFICARE"))
                else: # Se cancella il percorso duplicati, cancella anche da verificare
                    self.cartella_da_verificare_var.set("")
        
    def _log_message(self, message, flush=True): # flush è per compatibilità con _default_logger
        """ Aggiunge un messaggio all'area di log della GUI. """
        if self.log_area:
            self.log_area.config(state=tk.NORMAL)
            self.log_area.insert(tk.END, message + "\n")
            self.log_area.see(tk.END) # Scroll automatico all'ultimo messaggio
            self.log_area.config(state=tk.DISABLED)
            self.root.update_idletasks() # Aggiorna la GUI

    def pulisci_log(self):
        self.log_area.config(state=tk.NORMAL)
        self.log_area.delete(1.0, tk.END)
        self.log_area.config(state=tk.DISABLED)
        self._log_message("Log pulito.")

    def _update_progress_bar(self, corrente, totale):
        """ Aggiorna la barra di progresso della GUI. """
        if self.progress_bar:
            if totale > 0:
                percentuale = int((corrente / totale) * 100)
                self.progress_bar['value'] = percentuale
            else: # Se totale è 0, resetta la barra
                self.progress_bar['value'] = 0
            self.root.update_idletasks() # Necessario per aggiornare la GUI da un thread

    def abilita_controlli(self, abilita=True):
        stato = tk.NORMAL if abilita else tk.DISABLED
        # Abilita/Disabilita i campi di input e i bottoni sfoglia
        for child in self.root.winfo_children(): # Cerca in tutti i frame
            if isinstance(child, ttk.LabelFrame) and child.cget('text') == "Percorsi Cartelle":
                for widget in child.winfo_children():
                    if isinstance(widget, (ttk.Entry, ttk.Button)):
                         try: widget.config(state=stato) # Alcuni widget potrebbero non avere 'state'
                         except tk.TclError: pass 
            elif isinstance(child, ttk.Frame):
                 for sub_child in child.winfo_children(): # Cerca anche nei sotto-frame (es. action_frame)
                    if isinstance(sub_child, ttk.LabelFrame) and sub_child.cget('text') == "Percorsi Cartelle":
                        for widget in sub_child.winfo_children():
                            if isinstance(widget, (ttk.Entry, ttk.Button)):
                                try: widget.config(state=stato)
                                except tk.TclError: pass
                    elif isinstance(sub_child, ttk.Frame): # action_frame
                        for widget in sub_child.winfo_children():
                            if isinstance(widget, ttk.Button) and widget.cget('text') == "Avvia Analisi":
                                try: widget.config(state=stato)
                                except tk.TclError: pass
        if self.avvia_button:
            self.avvia_button.config(state=stato)
        # self.stop_button.config(state=tk.NORMAL if not abilita else tk.DISABLED) # Logica per il bottone stop


    def _esegui_analisi(self):
        """ Contiene la logica effettiva dell'analisi, da eseguire in un thread. """
        self.abilita_controlli(False)
        self.progress_bar['value'] = 0 # Resetta la barra all'inizio
        self._log_message("--- Avvio Analisi --- ")
        try:
            cartella_musicale = self.cartella_musicale_var.get()
            cartella_duplicati = self.cartella_duplicati_var.get()
            cartella_non_conformi = self.cartella_non_conformi_var.get()
            # Il percorso DA VERIFICARE è derivato e già in self.cartella_da_verificare_var

            if not cartella_musicale:
                self._log_message("ERRORE: Selezionare la cartella musicale.")
                self.abilita_controlli(True)
                return

            # Default se i campi sono vuoti (dovrebbero essere già impostati da seleziona_cartella, ma per sicurezza)
            path_musicale = Path(cartella_musicale).resolve()
            path_duplicati = Path(cartella_duplicati if cartella_duplicati else path_musicale / "DOPPIONI").resolve()
            path_non_conformi = Path(cartella_non_conformi if cartella_non_conformi else path_musicale / "NON CONFORMI").resolve()
            path_da_verificare = Path(self.cartella_da_verificare_var.get() if self.cartella_da_verificare_var.get() else path_duplicati / "DA_VERIFICARE").resolve()
            
            self._log_message(f"Cartella musicale: {path_musicale}")
            self._log_message(f"Cartella duplicati: {path_duplicati}")
            self._log_message(f"Cartella non conformi: {path_non_conformi}")
            self._log_message(f"Cartella da verificare: {path_da_verificare}") # Log del nuovo percorso

            # Chiamata alla logica di business
            avvia_gestione_duplicati(
                path_musicale,
                path_duplicati,
                path_non_conformi,
                path_da_verificare, # Aggiunto il nuovo percorso
                logger=self._log_message, # Passa il logger della GUI
                progress_callback=self._update_progress_bar # Passa il callback per la progress bar
            )
            self._log_message("--- Analisi Completata ---")
            self.progress_bar['value'] = 100 # Assicura che sia al 100% alla fine (se tutto ok)

        except Exception as e:
            self._log_message(f"ERRORE CRITICO DURANTE L'ANALISI: {e}")
            import traceback
            self._log_message(traceback.format_exc())
        finally:
            self.abilita_controlli(True)

    def avvia_analisi_thread(self):
        """ Avvia l'analisi in un thread separato per non bloccare la GUI. """
        # Verifica preliminare che la cartella musicale sia selezionata
        if not self.cartella_musicale_var.get():
            self._log_message("ERRORE: La cartella musicale deve essere specificata.")
            tk.messagebox.showerror("Errore", "Specificare la cartella musicale prima di avviare l'analisi.")
            return
        
        # Crea e avvia il thread
        analysis_thread = threading.Thread(target=self._esegui_analisi, daemon=True)
        analysis_thread.start()

if __name__ == '__main__':
    root = tk.Tk()
    app = AppGestoreMusicaleV0_1(root)
    root.mainloop() 