import easyocr

reader = easyocr.Reader(['ch_sim','en'])
results = reader.readtext("test.png")

for _, text, _ in results:
    print(text)