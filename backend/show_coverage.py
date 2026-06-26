import xml.etree.ElementTree as ET

tree = ET.parse('coverage.xml')
root = tree.getroot()

lines_valid = root.get('lines-valid')
lines_covered = root.get('lines-covered')
line_rate = float(root.get('line-rate'))
percent = round(line_rate * 100, 1)

print('=' * 40)
print('   COBERTURA TOTAL DEL PROYECTO')
print('=' * 40)
print(f'   Lineas totales:    {lines_valid}')
print(f'   Lineas cubiertas:  {lines_covered}')
print(f'   Cobertura:         {percent}%')
print()
if percent >= 70:
    print('   Resultado: META CUMPLIDA (objetivo 70%) ✅')
else:
    print(f'   Resultado: FALTA {(70 - percent)}% para la meta')
print('=' * 40)