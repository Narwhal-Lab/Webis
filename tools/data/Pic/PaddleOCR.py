from paddleocr import PaddleOCR

ocr = PaddleOCR(use_angle_cls=True, lang="ch")
img_path = r"C:\\Users\\yuzhe\\Desktop\\test\\test.png"
result = ocr.ocr(img_path, cls=True)

print("识别结果：\n")
for line in result[0]:
    print(line[1][0])