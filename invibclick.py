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

def on_key_press(key):
    global play
    if key == keyboard.KeyCode.from_char('p'):  # Verifica se a tecla pressionada é o p
        if play:
            print("Parando...")
            play = False
        else:
            print("Iniciando...")
            play = True
            comecaOAtk()
                
            

def comecaOAtk():
    """
    Função principal que inicia o ataque.
    """
    global play
    if play:
        # Coloque aqui o código do ataque que você deseja executar
        print("Atacando, selecione a invisibilidade...")
        pyautogui.click()
        time.sleep(4.1)  # espera pra prox invib
    if play:    
        print("Joga inivib 1...")
        pyautogui.click()
        time.sleep(9.5)  # espera pra prox invib
    if play:
        print("Joga inivib 2...")
        pyautogui.click()
        time.sleep(9.2)  # espera pra prox invib
    if play:            
        print("Joga inivib 3...")
        pyautogui.click()
        time.sleep(9.7)  # espera pra prox invib            
    if play:
        print("Joga inivib 4...")
        pyautogui.click()
        time.sleep(9.5)  # espera pra prox invib
    if play:
        print("Joga inivib 5...")
        pyautogui.click()
        time.sleep(9.5)  # espera pra prox invib
    if play:            
        print("Joga inivib 6...")
        pyautogui.click()
        time.sleep(9.5)  # espera pra prox invib            
    if play:
        print("Joga inivib 7...")
        pyautogui.click()
        
#-------- START
# Variáveis para armazenar as coordenadas da área selecionada

play = False


# Cria listeners para capturar eventos de teclado e mouse
keyboard_listener = keyboard.Listener(on_press=on_key_press)
keyboard_listener.start()

while True:
    
    if play == False:
        print("...")
        time.sleep(1)  
        
        