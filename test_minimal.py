from fpdf import FPDF

pdf = FPDF()
pdf.add_page()
pdf.set_font("Helvetica", "B", 16)
pdf.multi_cell(0, 10, "PubMed AI Summary")
print("First multi_cell succeeded. Current x:", pdf.x, "y:", pdf.y)

pdf.set_font("Helvetica", "", 11)
print("Page width:", pdf.w, "Left margin:", pdf.l_margin, "Right margin:", pdf.r_margin)
print("Current x:", pdf.x)
pdf.multi_cell(0, 8, "Topic: Paracetamol")
pdf.output("test_minimal.pdf")
print("Success!")