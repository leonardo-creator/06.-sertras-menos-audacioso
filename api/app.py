import logging
import requests
from flask import Flask, send_file, g
from io import BytesIO
import urllib.parse
import psutil
import os
from playwright.sync_api import sync_playwright
import pandas as pd

app = Flask(__name__)

# Configuração do logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def log_memory_usage():
    """ Função para monitorar o uso de memória durante a execução """
    process = psutil.Process(os.getpid())
    memory_usage = process.memory_info().rss / (1024 * 1024)  # Em MB
    logging.info(f"Uso de memória: {memory_usage:.2f} MB")

def login_and_download_excel(email, password, filter_inputs):
    log_memory_usage()  # Log do uso de memória antes do processo começar
    
    with sync_playwright() as p:
        logging.info("Iniciando o navegador.")
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        logging.info("Nova página criada.")

        try:
            logging.info("Navegando para a página de login.")
            page.goto("https://gestaodeterceiros.sertras.com/contratante/")
            logging.info("Aguarde enquanto a página é carregada.")

            logging.info("Preenchendo o campo de login.")
            page.fill("#edtLoginInfo", email)
            logging.debug(f"Campo de login preenchido com: {email}")

            logging.info("Preenchendo o campo de senha.")
            page.fill("#edtLoginSenha", password)
            logging.debug(f"Campo de senha preenchido com: {'*' * len(password)}")

            page.press("#btnLogin", "Enter")
            logging.info("Pressionando Enter para enviar o formulário de login.")

            logging.info("Aguardando redirecionamento após o login.")
            page.wait_for_url("https://gestaodeterceiros.sertras.com/contratante/dashboard/")
            logging.info("Login bem-sucedido, redirecionado para a página de relatórios.")

            urls = []
            logging.info("Construindo URLs para download.")
            for filtro in filter_inputs:
                excel_url = f"https://gestaodeterceiros.sertras.com/contratante/relatorio-integracao-status-integracao-pessoas-export/?filtro_recurso_descricao=&filtro_recurso_cpf_cnpj_placa_numero=&filtro_status=&filtro_nome_empresa_terceira=&filtro_cnpj_empresa_terceira=&filtro_numero_contrato={filtro.strip().replace(' ', '%20')}&filtro_funcao=&filtro_unidades="
                urls.append(excel_url)
                logging.debug(f"URL construída: {excel_url}")

            cookies = page.context.cookies()
            cookies_dict = {cookie['name']: cookie['value'] for cookie in cookies}
            logging.info("Obtendo cookies para o download.")
            logging.debug(f"Cookies obtidos: {cookies_dict}")

            log_memory_usage()  # Log do uso de memória antes de iniciar o download
            
            # Vamos baixar apenas o primeiro arquivo para este exemplo
            excel_url = urls[0]
            logging.info(f"Baixando o arquivo: {excel_url}")
            response = requests.get(excel_url, cookies=cookies_dict)

            if response.status_code == 200:
                logging.info("Download concluído, retornando o arquivo.")
                log_memory_usage()  # Log do uso de memória após o download
                return BytesIO(response.content)  # Retorna o conteúdo como BytesIO, em vez de salvar no disco
            else:
                logging.error(f"Erro ao baixar o arquivo: {response.status_code}")
                return None

        except Exception as e:
            logging.error(f"Ocorreu um erro: {e}")
        finally:
            browser.close()
            logging.info("Navegador fechado.")
            log_memory_usage()  # Log do uso de memória após fechar o navegador


@app.route('/download/<email>/<password>/<filters>', methods=['GET'])
def download_and_return_in_memory(email, password, filters):
    filters = urllib.parse.unquote(filters)
    logging.info(filters)

    filter_inputs = filters.split('*')
    logging.info(filter_inputs)

    logging.info(f"Processando download para: {email}")

    g.email = email

    # Faz o download do arquivo Excel
    excel_file = login_and_download_excel(email, password, filter_inputs)

    if excel_file:
        # Converte o conteúdo do Excel para um DataFrame pandas
        try:
            # Lê o conteúdo do arquivo Excel diretamente do BytesIO
            df = pd.read_excel(excel_file)

            # Converte o DataFrame para uma lista de dicionários (JSON-like)
            data_as_dict = df.to_dict(orient='records')

            # Retorna o JSON como resposta
            return jsonify(data_as_dict)

        except Exception as e:
            logging.error(f"Erro ao processar o arquivo Excel: {e}")
            return "Erro ao processar o arquivo Excel", 500

    else:
        return "Erro ao baixar o arquivo", 500

@app.after_request
def cleanup(response):
    # Limpa possíveis dados armazenados no g
    g.pop('email', None)
    return response

if __name__ == '__main__':
    app.run(debug=True)



##http://127.0.0.1:5000/download/leonardojuvencio@brkambiental.com.br/Lj@2024.senha%23%40%211/4165|4600011099|28.156.054(0001-60*2741|4600009799|11.070.002(0001-73

#https://zero6-sertras-menos-audacioso.onrender.com/download/leonardojuvencio@brkambiental.com.br/Lj@2024.senha%23%40%211/4165|4600011099|28.156.054(0001-60*2741|4600009799|11.070.002(0001-73