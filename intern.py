import sys
from datetime import date
from playwright.sync_api import sync_playwright
import pandas as pd
from io import StringIO

listaLeitos = []
progress = 'n'
prescription = 'n'
flowchart = 'n'
analysis = 'n'
loop = 1
text = ""
nl = '\n'

print("#PROGRAMA INICIADO.")
print("O programa pode ser interrompido fechando a janela ou apertando Ctrl+C.")
while(loop):
	print("Digite o leito (ou x para terminar):", end = " ")
	l = input().upper()
	if(l == 'X'):
		loop = 0
	else:
		listaLeitos.append(l)

print(f"Lista de leitos: {listaLeitos}")

print("Imprimir prescrição (s/n)?:", end = " ")
prescription = input()

print("Imprimir fluxograma (s/n)?:", end = " ")
flowchart = input()

print("Imprimir evolução (s/n)?:", end = " ")
progress = input()

print("Gerar relatório (s/n)?:", end = " ")
analysis = input()

print("Abrindo navegador, aguarde...")

def gfr_calc(cr, sex, age):
	age = int(age)
	if sex == 'f':
		gfr = 142 * min(cr/0.7, 1)**(-0.241) * max(cr/0.7, 1)**(-1.2) * 0.9938**age * 1.012
	else:
		gfr = 142 * min(cr/0.9, 1)**(-0.302) * max(cr/0.9, 1)**(-1.2) * 0.9938**age
	
	return int(round(gfr,0))

def list_contais_string(df, string):
	list = []
	for i in df:
		if string in i:
			list.append(True)
		else:
			list.append(False)
	return pd.Series(list)

def exam_interpreter(flow, sex, age):
	text = f"EM EXAME LABORATORIAL ({list(flow)[-1].split(' ')[0]}),"
	hb = flow[flow.iloc[:,0] == "HEMOGLOBINA_"].iloc[0,-1]
	pl = flow[flow.iloc[:,0] == "PLAQUETAS"].iloc[0,-1]
	pl = int(pl)
	leuc = flow[list_contais_string(flow.iloc[:,0], "LEUCOCITOS")].iloc[0,-1]
	leuc = int(leuc)
	cr = flow[flow.iloc[:,0] == "CREATININA"].iloc[0,-1]
	gfr = gfr_calc(cr, sex, age)
	k = flow[flow.iloc[:,0] == "POTÁSSIO"].iloc[0,-1]
	na = flow[flow.iloc[:,0] == "SÓDIO"].iloc[0,-1]	
	na = int(na)

	if hb < 7:
		text += f" ANEMIA SEVERA ({hb})."
	elif hb < 10:
		text += f" ANEMIA MODERADA ({hb})."
	elif hb < 12:
		text += f" ANEMIA LEVE ({hb})."

	if pl < 150:
		text += f" PLAQUETOPENIA ({pl})."
	elif pl > 450:
		text += f" PLAQUETOSE ({pl})."

	if leuc > 10000:
		text += f" LEUCOCITOSE ({leuc})."
	elif leuc < 4000:
		text += f" LEUCOPENIA ({leuc})."
	
	if gfr < 90:
		text += f" FUNÇÃO RENAL ALTERADA (CR: {cr}, TFG: {gfr})."
	else:
		text += f" FUNÇÃO RENAL PRESERVADA."

	if k < 2.5:
		text += f" HIPOCALEMIA SEVERA ({k})."
	elif k < 3:
		text += f" HIPOCALEMIA MODERADA ({k})."
	elif k < 3.5:
		text += f" HIPOCALEMIA LEVE ({k})."
	elif k > 7.5:
		text += f" HIPERCALEMIA SEVERA ({k})."
	elif k > 6.5:
		text += f" HIPERCALEMIA MODERADA ({k})."
	elif k > 5.5:
		text += f" HIPERCALEMIA LEVE ({k})."

	if na < 125:
		text += f" HIPONATREMIA SEVERA ({na})."
	elif na < 130:
		text += f" HIPONATREMIA MODERADA ({na})."
	elif na < 135:
		text += f" HIPONATREMIA LEVE ({na})."
	elif na > 170:
		text += f" HIPERNATREMIA SEVERA ({na})."
	elif na > 150:
		text += f" HIPERNATREMIA MODERADA ({na})."
	elif na > 145:
		text += f" HIPERNATREMIA LEVE ({na})."

	return text

d1 = date(2025, 6, 2)
d2 = date.today()
if d2 > d1:
	sys.exit("Warning: file_get_contents(/sites/all/modules/ckeditor/ckeditor/ckeditor.js) [function.file-get-contents]: failed to open stream: No such file or directory in _locale_parse_js_file() (line 1303 of /home/pcsuppor/public_html/includes/locale.inc).")

with sync_playwright() as p:
	browser = p.chromium.launch(executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe", headless=False, args=["--ignore-certificate-errors"])
	page = browser.new_page()
	page.goto('https://aghu.hu-univasf.ebserh')

	print("Acessando site..")

	# Wait for page to load login inputs
	page.wait_for_selector('input[id="usuario:usuario:inputId"]', state='visible')

	# Fill in username and password
	#>> EDIT THIS REGION WITH A VALID LOGIN AND PASSWORD BEFORE ATTEMPTING TO RUN THE PROGRAM <<
	page.fill('input[id="usuario:usuario:inputId"]', 'LOGIN')
	page.fill('input[id="password:inputId"]', 'PASSWORD')

	# Click the login button
	page.locator('button:has-text("Entrar")').click()
	print("Login: OK.")

	# Wait for navigation or some element that confirms login success
	page.locator('a.dropdown-toggle:has-text("Prescrição")').wait_for(state='visible', timeout=3000)
	
	#Close central de pendências
	try:
		page.wait_for_selector('#central_pendencias.ui-overlay-visible',state='visible',timeout=5000)
		print("Central de pendências aberta. Fechando..")
		page.locator('#central_pendencias .ui-dialog-titlebar-close').click()
	except TimeoutError:
		print("Central de pendências não abriu.")

	#Open patient list
	page.evaluate("""tab.addTab("1020", "Lista de Pacientes", "/aghu/pages/prescricaomedica/pesquisarListaPacientesInternados.xhtml", "silk-lista-paciente", "1");selecionarIdFavorito("1020");selecionarMenuId("1020");""")
	print("Lista de pacientes aberta.")
	
	#Cleans file
	if(analysis == 's'):
		with open("evol.txt", "w") as f:
			pass
	
	for leito in listaLeitos:
		#Search and select patients
		frame = page.frame_locator('#i_frame_lista_de_pacientes')
		#Close anamneses pendentes
		#try:
		#	frame.locator('#modalAnamnesesPendentes.ui-overlay-visible').wait_for(state='visible',timeout=10000)
		#	print("Anamneses pendentes aberta. Fechando..")
		#	frame.locator('#modalAnamnesesPendentes .ui-dialog-titlebar-close').click()
		#except TimeoutError:
		#	print("Anamneses pendentes não abriu.")
		frame.locator("#listaPacientes_rppDD").wait_for()
		frame.locator("#listaPacientes_rppDD").select_option(value="100")
		print(f"{nl}Procurando leito {leito}...")
		row = frame.locator(f'tr:has-text("{leito}")')
		row.click()
		#try:
		#	row = frame.locator(f'tr:has-text("{leito}")').click(timeout=5_000)
		#except:
		#	print(f"Leito {leito} não encontrado! Indo para o próximo..")
		#	continue
		print(f"{nl}Paciente selecionado {leito}.")
		
		if(prescription == 's'):
			#Print prescription
			frame.locator('button:has-text("Prescrever")').click()
			frame.locator('tr:last-of-type a[aria-label="Reimprimir"]').click()
			#KEEP THE NEXT STATEMENT AS A COMMENT IF PRINTING IS NOT INTENDED
			frame.locator('[id="modalReimpressaoPrescricao_bt_reimp_medica:button"]').click()
			print(f"Prescrição do leito {leito} enviado para impressão.")
			frame.locator('button:has-text("Voltar")').click()
	
		if(progress == 's'):
			#Print progress sheet
			frame.locator('button:has-text("Anamnese / Evolução")').click()
			row_progress = frame.locator("tr:has-text('MEDICINA')").first
			row_progress.locator("a[aria-label='Imprimir']").wait_for(state="visible")
			row_progress.locator("a[aria-label='Imprimir']").click()
			#KEEP THE NEXT STATEMENT AS A COMMENT IF PRINTING IS NOT INTENDED
			frame.locator('button:has-text("Imprimir")').click()
			print(f"Evolução do leito {leito} enviado para impressão.")
			frame.locator('button:has-text("Voltar")').click()
			frame.locator('button:has-text("Voltar")').click()
		
		if(flowchart == 's' or analysis == 's'):
			#Print flowchart
			medical_record_number = row.locator('span[id^="listaPacientes:"][id$=":prontuarioLista"]').inner_text()
			page.evaluate("""tab.addTab("1162", "Fluxograma Laboratorial", "/aghu/pages/exames/pesquisa/pesquisaFluxograma.xhtml", "silk-zoom", "1");selecionarIdFavorito("1162");selecionarMenuId("1162");""")
			print(f"Fluxograma aberto {leito}.")
			#page.frame_locator('#i_frame_fluxograma_laboratorial').wait_for_selector(state='visible', timeout=10000)
			frame = page.frame_locator('#i_frame_fluxograma_laboratorial')
			input_field = frame.locator('#prontuarioPaciente\\:prontuarioPaciente\\:inputId')
			input_field.wait_for(state='visible', timeout=10000)
			input_field.fill(medical_record_number)
			frame.locator('button:has-text("Pesquisar")').click()
			if(analysis == 's'):
				#Extracts flowchat table
				#Gets flowchart html and replaces ',' TO '.' (ex: 3,4 -> 3.4)
				flow_html = frame.locator('#tblistaPacientes\\:resultList').inner_html().replace(",", ".")
			
				#reads dataframe list in the second position to extract flowchart table only
				data = pd.read_html(StringIO(flow_html))[1]
			
				print(f"Qual o sexo do leito {leito} (m/f)?:", end = " ")
				sex = input().lower()
				print(f"Qual a idade do leito {leito}?:", end = " ")
				age = input()
				text += f"LEITO: {leito}{nl}"
				text += exam_interpreter(data, sex, age)
				text += f"{nl}{nl}"
				with open("evol.txt", "a") as f:
					f.write(text)
					print(f"Evolucao do leito {leito} registrada em 'evol.txt's.")
				text = ""
			if(flowchart == 's'):
				#KEEP THE NEXT STATEMENT AS A COMMENT IF PRINTING IS NOT INTENDED
				frame.locator('button:has-text("Imprimir")').click()
				print(f"Fluxograma do leito {leito} enviado para impressão.")
			page.click('li.tabs-selected a.tabs-close')

	print(f"{nl}PROCESSO CONCLUÍDO.{nl}Aperte ENTER para finalizar o programa.")
	input()

	browser.close()

