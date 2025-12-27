import pygame
import sys
import random
import numpy as np

# --- Inicialización con soporte de sonido ---
pygame.init()
try:
    pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
    SONIDO_DISPONIBLE = True
except:
    SONIDO_DISPONIBLE = False

# Configuración
ANCHO, ALTO = 720, 1280
pantalla = pygame.display.set_mode((ANCHO, ALTO), pygame.RESIZABLE)
pygame.display.set_caption("Desert Runner - 300m")

# Colores
CIAN = (0, 255, 255)
NEON_AZUL = (0, 200, 255)
AZUL_PULSO = (100, 255, 255)
NEGRO = (0, 0, 0)
BLANCO = (255, 255, 255)
VERDE = (0, 200, 0)
ROJO = (255, 0, 0)
GRIS_OSC = (10, 10, 20)
SUELO_COLOR = (139, 69, 19)
SUELO_SOMBRA = (101, 67, 33)
MONTANA_1 = (112, 128, 144)
MONTANA_2 = (95, 107, 122)
MONTANA_3 = (69, 82, 97)
NUBE_COLOR = (220, 230, 255)

# Fuentes
fuente = pygame.font.SysFont("Arial", 32)
fuente_a = pygame.font.SysFont("Arial", 60, bold=True)
fuente_ganaste = pygame.font.SysFont("Arial", 64, bold=True)
fuente_metros = pygame.font.SysFont("Arial", 30)

# --- Generación de sonidos ---
def generar_sonido(frecuencia, duracion_ms=200, tipo="seno"):
    if not SONIDO_DISPONIBLE:
        return None
    try:
        sample_rate = 22050
        n_samples = int(duracion_ms * sample_rate / 1000)
        t = np.linspace(0, duracion_ms / 1000, n_samples, False)
        if tipo == "cuadrado":
            wave = 0.5 * np.sign(np.sin(2 * np.pi * frecuencia * t))
        elif tipo == "click":
            wave = np.zeros(n_samples)
            wave[:int(0.005 * sample_rate)] = np.linspace(0.8, 0, int(0.005 * sample_rate))
        else:
            wave = np.sin(2 * np.pi * frecuencia * t)
        stereo_wave = np.column_stack((wave, wave))
        sound = pygame.sndarray.make_sound((stereo_wave * 32767).astype(np.int16))
        return sound
    except:
        return None

sonido_fondo = generar_sonido(110, 5000, "viento")
sonido_salto = generar_sonido(660, 150, "cuadrado")
sonido_paso = generar_sonido(300, 80, "click")

sonido_ganar = None
if SONIDO_DISPONIBLE:
    try:
        notas = [262, 330, 392, 523]
        duraciones = [200, 200, 200, 400]
        samples = []
        for f, d in zip(notas, duraciones):
            t = np.linspace(0, d/1000, int(22050 * d / 1000), False)
            wave = 0.3 * np.sin(2 * np.pi * f * t)
            if samples:
                wave = np.concatenate((np.zeros(int(22050 * 50 / 1000)), wave))
            samples.append(wave)
        full_wave = np.concatenate(samples)
        stereo = np.column_stack((full_wave, full_wave))
        sonido_ganar = pygame.sndarray.make_sound((stereo * 32767).astype(np.int16))
    except:
        pass

if sonido_fondo:
    sonido_fondo.play(-1)

# --- Juego ---
ESC_M = 100
scroll_x = 0.0
metros = 0
juego_terminado = False

ALTO_JUEGO = int(ALTO * 0.7)
SUELO_Y = ALTO_JUEGO - 70
jugador = pygame.Rect(ANCHO // 2 - 32, SUELO_Y - 48, 32, 48)
vel_y = 0
en_suelo = True
GRAVEDAD = 0.85
SALTO_VEL = -16

# Montañas
montanas = []
for i in range(6):
    base = random.randint(200, 400)
    montanas.append({
        "x": i * 1000 + random.randint(0, 500),
        "base": base,
        "altura": random.randint(100, 250),
        "v": 0.05 + i * 0.04,
        "color": [MONTANA_3, MONTANA_2, MONTANA_1][i % 3]
    })

# Nubes
nubes = []
for _ in range(5):
    nubes.append({
        "x": random.randint(0, ANCHO + 500),
        "y": random.randint(50, ALTO_JUEGO - 200),
        "v": random.uniform(0.04, 0.1)
    })

# Partículas (solo salto y estela)
particulas = [{"activo": False} for _ in range(250)]

# --- Gamepad Virtual ---
min_dim = min(ANCHO, ALTO)
radio_joystick = max(90, int(0.11 * min_dim))
radio_a = max(75, int(0.095 * min_dim))
margen = 30

centro_joystick = (radio_joystick + margen, ALTO - radio_joystick - margen)
centro_a = (ANCHO - radio_a - margen, ALTO - radio_a - margen)

joystick_izq = {
    "centro": centro_joystick,
    "radio_base": radio_joystick,
    "radio_thumb": int(radio_joystick * 0.65),
    "thumb": centro_joystick,
    "activo": False,
    "velocidad": 0.0
}

boton_a = {"centro": centro_a, "radio": radio_a}
TEXTO_A = fuente_a.render("A", True, NEGRO)

tocando_a = False
tocando_joystick = False

tiempo_inicio = pygame.time.get_ticks()
ultimo_pulso = tiempo_inicio
pulso_activo = False
ultimo_paso = tiempo_inicio

frame_correr = 0
ultima_actualizacion_frame = 0
velocidad_animacion = 80

# --- Funciones ---
def dibujar_montana_mejorada(x, y_base, altura, color):
    ancho1 = altura * 2.5
    pygame.draw.polygon(pantalla, color, [
        (x - ancho1//2, y_base),
        (x, y_base - altura),
        (x + ancho1//2, y_base)
    ])
    oscuro = (max(0, color[0]-20), max(0, color[1]-20), max(0, color[2]-20))
    ancho2 = altura * 1.8
    pygame.draw.polygon(pantalla, oscuro, [
        (x - ancho2//2, y_base - 20),
        (x, y_base - altura),
        (x + ancho2//2, y_base - 20)
    ])
    claro = (min(255, color[0]+30), min(255, color[1]+30), min(255, color[2]+30))
    ancho3 = altura * 0.6
    pygame.draw.polygon(pantalla, claro, [
        (x - ancho3//2, y_base - altura + 10),
        (x, y_base - altura),
        (x + ancho3//2, y_base - altura + 10)
    ])

def dibujar_nube_pixel(x, y):
    for dx, dy in [(-15,0), (0,-8), (0,0), (0,8), (15,0)]:
        pygame.draw.rect(pantalla, NUBE_COLOR, (x+dx, y+dy, 18, 18))
        pygame.draw.rect(pantalla, (240, 248, 255), (x+dx+4, y+dy+4, 10, 10))

def dibujar_jugador_ninja(x, y, velocidad_x, en_suelo, saltando):
    global frame_correr, ultima_actualizacion_frame
    ahora = pygame.time.get_ticks()
    vel_factor = max(0.5, 1.0 + abs(velocidad_x) * 0.3)
    if ahora - ultima_actualizacion_frame > int(velocidad_animacion / vel_factor):
        frame_correr = (frame_correr + 1) % 6
        ultima_actualizacion_frame = ahora

    # Cuerpo
    pygame.draw.rect(pantalla, NEGRO, (x + 6, y + 12, 20, 24))
    pygame.draw.rect(pantalla, NEON_AZUL, (x + 6, y + 28, 20, 4))

    # Cabeza y cabello
    pygame.draw.rect(pantalla, NEGRO, (x + 8, y - 4, 16, 20))
    parpadeo = (ahora % 2000 < 50)
    ojos_y = y + 4
    if parpadeo:
        pygame.draw.line(pantalla, BLANCO, (x + 12, ojos_y), (x + 14, ojos_y), 2)
        pygame.draw.line(pantalla, BLANCO, (x + 18, ojos_y), (x + 20, ojos_y), 2)
    else:
        pygame.draw.rect(pantalla, BLANCO, (x + 12, ojos_y, 2, 2))
        pygame.draw.rect(pantalla, BLANCO, (x + 18, ojos_y, 2, 2))
        pygame.draw.rect(pantalla, NEGRO, (x + 13, ojos_y + 1, 1, 1))
        pygame.draw.rect(pantalla, NEGRO, (x + 19, ojos_y + 1, 1, 1))

    offset_cabello = max(-8, min(8, int(velocidad_x * 1.8)))
    for i in range(5):
        dy = i * 2
        dx = offset_cabello * (1 - 0.2 * i)
        color = BLANCO if i % 2 == 0 else (200, 200, 200)
        pygame.draw.rect(pantalla, color, (x + 16 + dx, y - 6 + dy, 4, 2))
    if abs(velocidad_x) > 0.3:
        pygame.draw.rect(pantalla, BLANCO, (x + 6 + offset_cabello//2, y - 2, 3, 5))
        pygame.draw.rect(pantalla, BLANCO, (x + 26 - offset_cabello//2, y - 2, 3, 5))

    # Brazos
    brazo_izq_offsets = [(-6, 10), (-4, 8), (-2, 6), (0, 4), (2, 6), (4, 8)]
    brazo_der_offsets = [(26, 10), (28, 8), (30, 6), (32, 4), (30, 6), (28, 8)]
    if saltando:
        b_izq = (-2, -4)
        b_der = (22, -4)
    else:
        b_izq = brazo_izq_offsets[frame_correr]
        b_der = brazo_der_offsets[frame_correr]
    pygame.draw.rect(pantalla, NEGRO, (x + b_izq[0], y + b_izq[1], 6, 10))
    pygame.draw.rect(pantalla, NEON_AZUL, (x + b_izq[0] + 1, y + b_izq[1] + 1, 4, 8))
    pygame.draw.rect(pantalla, NEGRO, (x + b_der[0], y + b_der[1], 6, 10))
    pygame.draw.rect(pantalla, NEON_AZUL, (x + b_der[0] + 1, y + b_der[1] + 1, 4, 8))

    # Piernas
    pierna_izq_x, pierna_izq_y = x + 8, y + 36
    pierna_der_x, pierna_der_y = x + 18, y + 36
    if saltando:
        pierna_izq_y = pierna_der_y = y + 30
        pierna_izq_x, pierna_der_x = x + 10, x + 20
    else:
        if frame_correr < 3:
            pierna_izq_y -= 6; pierna_izq_x += 2
            pierna_der_y += 2; pierna_der_x -= 2
        else:
            pierna_der_y -= 6; pierna_der_x += 2
            pierna_izq_y += 2; pierna_izq_x -= 2
    pygame.draw.rect(pantalla, NEGRO, (pierna_izq_x, pierna_izq_y, 6, 12))
    pygame.draw.rect(pantalla, NEON_AZUL, (pierna_izq_x + 1, pierna_izq_y + 1, 4, 10))
    pygame.draw.rect(pantalla, NEGRO, (pierna_der_x, pierna_der_y, 6, 12))
    pygame.draw.rect(pantalla, NEON_AZUL, (pierna_der_x + 1, pierna_der_y + 1, 4, 10))
    pygame.draw.rect(pantalla, (30, 30, 50), (pierna_izq_x - 1, pierna_izq_y + 10, 8, 3))
    pygame.draw.rect(pantalla, (30, 30, 50), (pierna_der_x - 1, pierna_der_y + 10, 8, 3))

# --- Bucle principal ---
reloj = pygame.time.Clock()

while True:
    ahora = pygame.time.get_ticks()
    
    # --- Eventos ---
    for evento in pygame.event.get():
        if evento.type == pygame.QUIT:
            if sonido_fondo:
                sonido_fondo.stop()
            pygame.quit()
            sys.exit()
        
        if evento.type == pygame.VIDEORESIZE:
            ANCHO, ALTO = evento.w, evento.h
            pantalla = pygame.display.set_mode((ANCHO, ALTO), pygame.RESIZABLE)
            ALTO_JUEGO = int(ALTO * 0.7)
            SUELO_Y = ALTO_JUEGO - 70
            jugador.y = SUELO_Y - 48
            min_dim = min(ANCHO, ALTO)
            radio_joystick = max(90, int(0.11 * min_dim))
            radio_a = max(75, int(0.095 * min_dim))
            margen = 30
            joystick_izq["centro"] = (radio_joystick + margen, ALTO - radio_joystick - margen)
            boton_a["centro"] = (ANCHO - radio_a - margen, ALTO - radio_a - margen)
        
        if evento.type == pygame.MOUSEBUTTONDOWN:
            pos = evento.pos
            # Botón A
            dx_a = pos[0] - boton_a["centro"][0]
            dy_a = pos[1] - boton_a["centro"][1]
            if dx_a**2 + dy_a**2 <= boton_a["radio"]**2 and en_suelo and not juego_terminado:
                vel_y = SALTO_VEL
                en_suelo = False
                tocando_a = True
                if sonido_salto:
                    sonido_salto.play()
                for _ in range(5):
                    for p in particulas:
                        if not p["activo"]:
                            p.update({
                                "x": jugador.centerx + random.randint(-8, 8),
                                "y": jugador.bottom,
                                "vx": random.randint(-5, 5),
                                "vy": random.randint(-8, -4),
                                "vida": 25,
                                "activo": True
                            })
                            break
            # Joystick
            dx_j = pos[0] - joystick_izq["centro"][0]
            dy_j = pos[1] - joystick_izq["centro"][1]
            dist = (dx_j**2 + dy_j**2)**0.5
            if dist <= joystick_izq["radio_base"] + 40:
                tocando_joystick = True
        
        if evento.type == pygame.MOUSEMOTION and tocando_joystick and not juego_terminado:
            pos = evento.pos
            dx = pos[0] - joystick_izq["centro"][0]
            dy = pos[1] - joystick_izq["centro"][1]
            dist = (dx**2 + dy**2)**0.5
            if dist > joystick_izq["radio_base"]:
                dx = dx / dist * joystick_izq["radio_base"]
                dy = dy / dist * joystick_izq["radio_base"]
            joystick_izq["thumb"] = (joystick_izq["centro"][0] + dx, joystick_izq["centro"][1] + dy)
            joystick_izq["velocidad"] = max(-1.0, min(1.0, dx / joystick_izq["radio_base"] * 1.2))
        
        if evento.type == pygame.MOUSEBUTTONUP:
            tocando_a = tocando_joystick = False
            joystick_izq["thumb"] = joystick_izq["centro"]
            joystick_izq["velocidad"] = 0.0

        # Reinicio
        if evento.type == pygame.MOUSEBUTTONDOWN and juego_terminado:
            pos = evento.pos
            boton_r_centro = (ANCHO // 2, ALTO - 120)
            dx_r = pos[0] - boton_r_centro[0]
            dy_r = pos[1] - boton_r_centro[1]
            if dx_r**2 + dy_r**2 <= radio_a**2:
                scroll_x = 0.0
                metros = 0
                juego_terminado = False
                jugador.x = ANCHO // 2 - 32
                jugador.y = SUELO_Y - 48
                vel_y = 0
                en_suelo = True
                for m in montanas:
                    m["x"] = random.randint(0, 3000) + m["x"] % 1000
                for n in nubes:
                    n["x"] = random.randint(0, ANCHO + 500)
                if sonido_fondo:
                    sonido_fondo.play(-1)

    # --- Lógica ---
    if not juego_terminado:
        veloc_x = joystick_izq["velocidad"] * 12
        scroll_x += veloc_x
        if scroll_x < 0:
            scroll_x = 0
        metros = int(scroll_x / ESC_M)

        # Montañas: solo si hay movimiento
        if abs(veloc_x) > 0.1:
            for m in montanas:
                m["x"] -= veloc_x * m["v"]

        # Nubes: siempre
        for n in nubes:
            n["x"] -= n["v"] * 8
            if n["x"] < -100:
                n["x"] = ANCHO + random.randint(0, 300)
                n["y"] = random.randint(50, ALTO_JUEGO - 200)

        # Gravedad
        jugador.y += vel_y
        vel_y += GRAVEDAD
        if jugador.bottom >= SUELO_Y:
            jugador.bottom = SUELO_Y
            en_suelo = True
            vel_y = 0
        else:
            en_suelo = False

        # Sonido de pasos y estela
        if en_suelo and abs(veloc_x) > 0.5 and ahora - ultimo_paso > 250:
            if sonido_paso:
                sonido_paso.play()
            ultimo_paso = ahora
            for _ in range(2):
                for p in particulas:
                    if not p["activo"]:
                        p.update({
                            "x": jugador.centerx + random.randint(-10, 10),
                            "y": jugador.bottom + 5,
                            "vx": veloc_x * 0.5 + random.uniform(-1, 1),
                            "vy": random.uniform(-1, 0.5),
                            "vida": 40,
                            "color_base": random.choice([(0, 200, 255), (100, 255, 255), (200, 255, 255)]),
                            "activo": True
                        })
                        break

        # Partículas (salto + estela)
        for p in particulas:
            if p["activo"]:
                p["x"] += p.get("vx", 0)
                p["y"] += p.get("vy", 0)
                if "vy" in p:
                    p["vy"] += 0.1
                p["vida"] -= 1
                if p["vida"] <= 0 or p["y"] > ALTO or p["x"] < -50 or p["x"] > ANCHO + 50:
                    p["activo"] = False

        # Victoria
        if metros >= 300:
            juego_terminado = True
            if sonido_fondo:
                sonido_fondo.stop()
            if sonido_ganar:
                sonido_ganar.play()

    # --- Pulso neón ---
    if not juego_terminado and en_suelo:
        if ahora - ultimo_pulso > 2000:
            ultimo_pulso = ahora
            pulso_activo = True
            pulso_fin = ahora + 250
        if pulso_activo and ahora > pulso_fin:
            pulso_activo = False

    # --- Dibujar ---
    pantalla.fill(GRIS_OSC)

    # Nubes
    for n in nubes:
        x = int(n["x"])
        if -100 < x < ANCHO + 100:
            dibujar_nube_pixel(x, int(n["y"]))

    # Montañas
    for m in montanas:
        x = int(m["x"])
        if -500 < x < ANCHO + 500:
            dibujar_montana_mejorada(x, SUELO_Y, m["altura"], m["color"])

    # Suelo
    for i in range(-2, int(ANCHO / 50) + 3):
        x_s = int(-scroll_x) % 50 + i * 50
        pygame.draw.rect(pantalla, SUELO_COLOR, (x_s, SUELO_Y, 50, 70))
        pygame.draw.rect(pantalla, SUELO_SOMBRA, (x_s + 8, SUELO_Y + 5, 34, 8))
        for j in range(3):
            pygame.draw.rect(pantalla, (160, 120, 80), (x_s + 12 + j*12, SUELO_Y + 20, 5, 3))

    # Bandera
    if metros >= 290:
        bandera_x = ANCHO // 2 + (30000 - scroll_x)
        if bandera_x > -30:
            pygame.draw.rect(pantalla, (139, 69, 19), (int(bandera_x), SUELO_Y - 100, 6, 100))
            pygame.draw.rect(pantalla, VERDE, (int(bandera_x) + 6, SUELO_Y - 100, 30, 20))
            pygame.draw.rect(pantalla, ROJO, (int(bandera_x) + 6, SUELO_Y - 80, 30, 20))

    # Jugador
    dibujar_jugador_ninja(jugador.x, jugador.y, joystick_izq["velocidad"], en_suelo, vel_y < 0)

    # Partículas (estela y salto)
    for p in particulas:
        if p["activo"] and "color_base" in p:
            fade = max(0, p["vida"] / 40)
            color = tuple(int(c * fade) for c in p["color_base"])
            pygame.draw.circle(pantalla, color, (int(p["x"]), int(p["y"])), int(3 * fade))

    # Separador
    pygame.draw.line(pantalla, (50, 50, 70), (0, ALTO_JUEGO), (ANCHO, ALTO_JUEGO), 3)

    # Gamepad
    pygame.draw.circle(pantalla, (50, 50, 80), joystick_izq["centro"], joystick_izq["radio_base"])
    pygame.draw.circle(pantalla, (120, 150, 200), joystick_izq["centro"], joystick_izq["radio_base"], 3)
    thumb_color = (255, 255, 255) if tocando_joystick else (200, 220, 255)
    pygame.draw.circle(pantalla, thumb_color, joystick_izq["thumb"], joystick_izq["radio_thumb"])
    pygame.draw.circle(pantalla, CIAN, joystick_izq["thumb"], joystick_izq["radio_thumb"], 2)

    color_a = AZUL_PULSO if pulso_activo else NEON_AZUL
    pygame.draw.circle(pantalla, color_a, boton_a["centro"], boton_a["radio"])
    pygame.draw.circle(pantalla, CIAN, boton_a["centro"], boton_a["radio"], 4)
    if tocando_a:
        pygame.draw.circle(pantalla, BLANCO, boton_a["centro"], boton_a["radio"] - 20, 4)
    pantalla.blit(TEXTO_A, TEXTO_A.get_rect(center=boton_a["centro"]))

    # Victoria + Reiniciar
    if juego_terminado:
        overlay = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 220))
        pantalla.blit(overlay, (0, 0))
        txt1 = fuente_ganaste.render("¡GANASTE!", True, (0, 255, 200))
        txt2 = fuente.render("300 metros completados", True, BLANCO)
        pantalla.blit(txt1, txt1.get_rect(center=(ANCHO//2, ALTO//2 - 60)))
        pantalla.blit(txt2, txt2.get_rect(center=(ANCHO//2, ALTO//2 + 10)))

        boton_r_centro = (ANCHO // 2, ALTO - 120)
        pygame.draw.circle(pantalla, VERDE, boton_r_centro, radio_a)
        pygame.draw.circle(pantalla, BLANCO, boton_r_centro, radio_a, 3)
        TXT_RST = fuente_a.render("↻", True, BLANCO)
        pantalla.blit(TXT_RST, TXT_RST.get_rect(center=boton_r_centro))

    # Contador
    txt_m = fuente_metros.render(f"{metros} m", True, BLANCO)
    pantalla.blit(txt_m, (20, 20))

    pygame.display.flip()
    reloj.tick(60)
