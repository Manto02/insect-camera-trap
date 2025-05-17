import cv2

imm = cv2.imread("./prova.jpg")
cv2.imshow("prova", imm)
cv2.waitKey(0)
cv2.destroyAllWindows()