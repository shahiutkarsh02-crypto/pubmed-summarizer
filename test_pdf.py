from fpdf import FPDF

pdf = FPDF()
pdf.set_margins(15, 15, 15)
pdf.set_auto_page_break(auto=True, margin=15)
pdf.add_page()
pdf.set_font("Helvetica", "B", 16)
pdf.multi_cell(0, 10, "PubMed AI Summary")
pdf.set_font("Helvetica", "", 11)
pdf.multi_cell(0, 8, "Topic: Paracetamol")
pdf.output("test_output.pdf")
print("Success!")