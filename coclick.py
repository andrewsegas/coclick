import pytesseract
from PIL import ImageGrab
from pynput import keyboard, mouse
import threading
import os
import square
import configparser
import pydirectinput
import random
import re
import winsound
import pyautogui
import time


# Função para capturar a tela
def capture_screen():
    screenshot = ImageGrab.grab()
    return screenshot

# Função para processar a imagem e extrair o texto usando OC
def process_image(image):
    global moneyWant
    # Corta a imagem usando as coordenadas da área selecionada
    cropped_image = image.crop((posicoes.get("square1")[0], posicoes.get("square1")[1], posicoes.get("square2")[0], posicoes.get("square2")[1]))
    text = pytesseract.image_to_string(cropped_image)
    # Procura por um valor numérico no texto extraído
    lines = text.strip().split('\n')
    for i in range(3):
        if i < len(lines):
            num_str = re.sub(r'[^\d]', '', lines[i])  # Remove tudo exceto dígitos
            if num_str:
                moneyWant[i] = int(num_str)
                print(f"Valor encontrado {i+1}:", moneyWant[i])
            else:
                moneyWant[i] = 0
        else:
            moneyWant[i] = 0
    return

# Função chamada quando uma tecla é pressionada
def on_key_press(key):
    global play
    if play == False:
        if key == keyboard.KeyCode.from_char('0'):  # Verifica se a tecla pressionada é o 0
                print("Selecione a área da tela para Leitura:")
                areaOCR.start()
        
        if key == keyboard.KeyCode.from_char('9'):  # Verifica se a tecla pressionada é o 9
            nextX = pyautogui.position()  # Posição atual do mouse            
            salvar_posicao('square1', (areaOCR.start_x, areaOCR.start_y) )
            salvar_posicao('square2', (areaOCR.end_x, areaOCR.end_y) )
            salvar_posicao('next', nextX)
                
        if key == keyboard.KeyCode.from_char('8'):  # Verifica onde comeca o ataque
            atack = pyautogui.position()
            salvar_posicao('atack', atack)  
            
        if key == keyboard.KeyCode.from_char('7'):  # Verifica onde acaba o ataque
            atack2 = pyautogui.position()
            salvar_posicao('atack2', atack2)    
        
        if key == keyboard.KeyCode.from_char('6'):  # Terminar
            termina = pyautogui.position()
            salvar_posicao('termina', termina)      
        
        if key == keyboard.KeyCode.from_char('5'):  # ok
            ok = pyautogui.position()
            salvar_posicao('ok', ok)        
        
        if key == keyboard.KeyCode.from_char('4'):  # Voltar
            voltar = pyautogui.position()
            salvar_posicao('voltar', voltar)      

        if key == keyboard.KeyCode.from_char('3'):  # Atacar
            atacar = pyautogui.position() 
            salvar_posicao('atacar', atacar)     

        if key == keyboard.KeyCode.from_char('2'):  # Procurar
            procurar = pyautogui.position()
            salvar_posicao('procurar', procurar)

    if key == keyboard.KeyCode.from_char('p'):  # Verifica se a tecla pressionada é o p
        if play:
            print("Parando...")
            play = False
        else:
            print("Iniciando...")
            coloca_pra_atacar()
            play = True

def startAttack():
    ajustar_click()
    print("Começa")
    pydirectinput.press('1')  
    pydirectinput.press('1')  
    
    # cliica pra arrastar
    pyautogui.moveTo(posicoes.get("atack"), duration=0.3)
    pyautogui.click()

    pyautogui.mouseDown()
    time.sleep(1)
    pyautogui.moveTo(posicoes.get("atack2"), duration=1)  # Move o mouse para a posição final
    pyautogui.mouseUp()
    
    # Coloca todo o resto
    pyautogui.moveTo((posicoes.get("atack")[0]+posicoes.get("atack2")[0]) /2 , (posicoes.get("atack")[1]+posicoes.get("atack2")[1]) /2, duration = random.uniform(1,2) )  # Move o mouse para a posição final
    pyautogui.click()
    pyautogui.click()
    pydirectinput.press('z')
    pydirectinput.press('z')
    pyautogui.click()
    pydirectinput.press('q')
    pydirectinput.press('q')
    pyautogui.click()
    pydirectinput.press('w')
    pydirectinput.press('w')
    pyautogui.click()
    pydirectinput.press('e')
    pydirectinput.press('e')
    pyautogui.click()
    pydirectinput.press('r')
    pydirectinput.press('r')
    pyautogui.click()
    pydirectinput.press('a')
    pydirectinput.press('a')
    pyautogui.mouseDown()
    time.sleep(1)
    pyautogui.mouseUp()
    pyautogui.click()
    pyautogui.click()
    pyautogui.click()
    pyautogui.click()
    pyautogui.click()
    pyautogui.click()
    pyautogui.click()
    pyautogui.click()
    pyautogui.click()
    pyautogui.click()
    
    time.sleep(random.uniform(5,15))
    pydirectinput.press('q')
    time.sleep(random.uniform(0,1))
    pydirectinput.press('w')
    time.sleep(random.uniform(0,2))
    pydirectinput.press('e')
    time.sleep(random.uniform(0,1))
    pydirectinput.press('r')
        
    if ataque_info['star'] == 1 or (ataque_info['star'] == 2 and random.uniform(1,10) > 5):
        # entra se star 1 ou se for 2 50% das vezes
        # espera o ataque acabar 
        time.sleep(random.uniform(45,56))
    
    pyautogui.moveTo(posicoes.get("termina")[0] + round(random.uniform(-5,5)), posicoes.get("termina")[1] + round(random.uniform(-5,5)))  
    pyautogui.click()
    
    time.sleep(random.uniform(2,3))
    pyautogui.moveTo(posicoes.get("ok")[0] + round(random.uniform(-5,5)), posicoes.get("ok")[1] + round(random.uniform(-5,5)) )  
    pyautogui.click()
    
    time.sleep(random.uniform(2,3))
    pyautogui.moveTo(posicoes.get("voltar")[0] + round(random.uniform(-5,5)), posicoes.get("voltar")[1] + round(random.uniform(-5,5)))  
    pyautogui.click()
    
    time.sleep(2)
    coloca_pra_atacar()
    
    
    ajustar_click()
    print("Iniciando o proximo farm...")

def coloca_pra_atacar():
    time.sleep(random.uniform(2,3))
    pyautogui.moveTo(posicoes.get("atacar")[0] + round(random.uniform(-5,5)), posicoes.get("atacar")[1] + round(random.uniform(-5,5)))  
    pyautogui.click()
    
    time.sleep(random.uniform(2,3))
    pyautogui.moveTo(posicoes.get("procurar")[0] + round(random.uniform(-5,5)), posicoes.get("procurar")[1] + round(random.uniform(-5,5)))  
    pyautogui.click()
        
def check_attack(ataque_info):
    global play, vilacheck
    # Verifica se o valor é maior
    if moneyWant[0] > ataque_info['gold'] and moneyWant[1] > ataque_info['elixir'] and moneyWant[2] > ataque_info['blackelixir']: 
        #winsound.Beep(400, 200)  # 400 Hz por 200 milissegundos
        #winsound.Beep(400, 200)  # 400 Hz por 200 milissegundos
        print("Ataca esse")
        vilacheck = 0
        startAttack()
        
    elif vilacheck > 10 or ataque_info['star'] == 3:
        print("ataca de q q jeito")
        vilacheck = 0
        startAttack()
    else:
        print("Não ataca esse")
        click_next()
    
def click_next():
    pyautogui.click(posicoes.get("next"))
    print("proximo")
    time.sleep(2)
    ajustar_click()
    
def ajustar_click():
    # cliica pra arrastar
    print("ajusta-tela")
    pyautogui.moveTo(posicoes.get("square2"), duration=0.3)
    pyautogui.mouseDown()
    # clica pra arrastar
    pyautogui.moveTo(posicoes.get("next"), duration=0.3)  # Move o mouse para a posição do próximo botão
    pyautogui.mouseUp()


def salvar_posicao(nome, posicao, arquivo='config.ini'):
    config = configparser.ConfigParser()
    print("Salva: ", nome)
    # Se o arquivo existir, carrega o conteúdo
    if os.path.exists(arquivo):
        config.read(arquivo)

    # Garante que a seção exista
    if 'Posicoes' not in config:
        config['Posicoes'] = {}

    # Salva ou atualiza a posição
    x, y = posicao
    config['Posicoes'][nome] = f"{x},{y}"

    # Escreve no arquivo
    with open(arquivo, 'w') as configfile:
        config.write(configfile)


def carregar_ini(arquivo='config.ini'):
    config = configparser.ConfigParser()
    config.read(arquivo)

    dados = {}

    for secao in config.sections():
        dados[secao] = {}
        for chave, valor in config[secao].items():
            # Tenta converter para tupla se for posição
            if ',' in valor and all(v.strip().isdigit() for v in valor.split(',')):
                try:
                    x_str, y_str = valor.split(',')
                    dados[secao][chave] = (int(x_str), int(y_str))
                    continue
                except ValueError:
                    pass
            # Tenta converter para inteiro se possível
            if valor.isdigit():
                dados[secao][chave] = int(valor)
            else:
                dados[secao][chave] = valor

    return dados

def desligar_programa():
    print("fim do tempo! Encerrando...")
    os._exit(0) # encerrar imediatamente

def iniciar_temporizador():
    config = configparser.ConfigParser()
    config.read('config.ini')  # nome do seu arquivo ini

    try:
        minutos = float(config.get('Tempo', 'desligar_em_minutos'))
        segundos = minutos * 60
        t = threading.Timer(segundos, desligar_programa)
        t.start()
        print(f"Vai encerrar em  {minutos} minutos")   
    except Exception as e:
        print(f"executar por tempo ilimitado {e}")

    
    
#-------- START
# Variáveis para armazenar as coordenadas da área selecionada
areaOCR = square.Quadrado()
valores_config = carregar_ini()

posicoes = valores_config['Posicoes']
ataque_info = valores_config['Ataque']

moneyWant = [0, 0, 0]  # Lista para armazenar os valores

play = False
trofeus = 0


# Cria listeners para capturar eventos de teclado e mouse
keyboard_listener = keyboard.Listener(on_press=on_key_press)

# Inicia os listeners
keyboard_listener.start()
tenta_ler = 0
vilacheck = 0
corrige_atack = 0
iniciar_temporizador()

while True:
    print("...")
    time.sleep(1)  
    
    if play == True:
        print("Verificando...")
        valores_config = carregar_ini()
        posicoes = valores_config['Posicoes']
        ataque_info = valores_config['Ataque']
        # Captura a tela e processa a imagem
        image = capture_screen()
        process_image(image)
        if corrige_atack > 5:
            coloca_pra_atacar()
            corrige_atack = 0  
        
        if moneyWant[0] > 0 and moneyWant[1] > 0 and moneyWant[2] > 0: # tinha vila e pegou valor
                vilacheck += 1
                corrige_atack = 0
                check_attack(ataque_info)
        else:   
            print("Sem valor - ajusta")
            tenta_ler += 1
            if tenta_ler > 2:
                vilacheck += 1
                corrige_atack += 1 #variavel para colocar pra atacar quando buga
                click_next()
                tenta_ler = 0
            ajustar_click()
        
        