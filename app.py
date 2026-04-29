from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import os
import uuid
from fastapi.staticfiles import StaticFiles
from datetime import datetime
import math
from num2words import num2words

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("invoices", exist_ok=True)

app.mount("/invoices", StaticFiles(directory="invoices"), name="invoices")

def calculate_rounding(amount):
    net_amount = math.ceil(amount)

    round_off = net_amount - amount

    return net_amount, round(round_off,2)

def amount_to_words_inr(amount):
    # Split rupees and paise
    rupees = int(amount)
    paise = int(round((amount - rupees) * 100))
    
    words = num2words(rupees, lang='en_IN').title() + " Rupees"
    
    if paise > 0:
        words += " And " + num2words(paise, lang='en_IN').title() + " Paise"
    
    return words + " Only"

def format_date(d):
    if not d:
        return ""
    return datetime.strptime(d, "%Y-%m-%d").strftime("%d-%m-%Y")

def generate_pdf(data, filename):
    doc = SimpleDocTemplate(filename, pagesize=A4, rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20)
    elements = []
    styles = getSampleStyleSheet()

    # Custom Styles
    title_style = ParagraphStyle('Title', parent=styles['Normal'], fontSize=18, alignment=1, leading=16, fontName='Helvetica-Bold')
    sub_style = ParagraphStyle('Sub', parent=styles['Normal'], fontSize=8, alignment=1, leading=10, spaceBefore=4)
    label_style = ParagraphStyle('Label', parent=styles['Normal'], fontSize=8, leading=9)
    bold_label = ParagraphStyle('BoldLabel', parent=styles['Normal'], fontSize=8, fontName='Helvetica-Bold')

    # --- 1. HEADER SECTION ---
    header_data = [
        [Paragraph("Pushpa Enterprises", title_style), ""],
        [Paragraph("A-2, Arihant Ind. Estate, W. Exp. Highway<br/>(Parmar Tecno Center Compound)<br/>Pelhar Village, Vasai Phata, Vasai (E)<br/><br/>GSTIN/UIN: 27AFHFS4085F1ZQ<br/>PAN No: AFHFS4085F", sub_style), ""]
    ]
    header_table = Table(header_data, colWidths=[450, 100])
    header_table.setStyle(TableStyle([
        ('SPAN', (0, 0), (1, 0)),
        ('SPAN', (0, 1), (1, 1)),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 0.1 * inch))

    # --- 2. INVOICE INFO & ADDRESS SECTION ---
    # Top Row: Invoice Title
    elements.append(Paragraph("<b>Tax Invoice</b>", title_style))
    elements.append(Paragraph("(As per rule 7 and section 3 of GST Act 2017)", sub_style))
    elements.append(Spacer(1, 5))

    rec_details = f"<b>Details of Receiver (Billed To)</b><br/><br/>{data['receiver_add'].replace("\n","<br/>")}"
    con_details = f"<b>Details of Consignee (Shipped To)</b><br/><br/>{data['consignee_add'].replace("\n","<br/>")}"
    invoice_details = f"""Invoice No&nbsp;&nbsp;:&nbsp;&nbsp;{data['invoice_no']}<hr><br/>
                        Invoice &nbsp;&nbsp;:&nbsp;&nbsp;{format_date(data['invoice_date'])}<hr><br/>
                        Invoice Time&nbsp;&nbsp;:&nbsp;&nbsp;{data['invoice_time']}<hr><br/>
                        Order No&nbsp;&nbsp;:&nbsp;&nbsp;{data['order_no']}<hr><br/>
                        Order Date&nbsp;&nbsp;:&nbsp;&nbsp;{format_date(data['order_date'])}<hr><br/>
                        LR No&nbsp;&nbsp;:&nbsp;&nbsp;{data['lr_no']}<hr><br/>
                        LR Date&nbsp;&nbsp;:&nbsp;&nbsp;{data['lr_date']}<hr><br/>
                        Vehicle No&nbsp;&nbsp;:&nbsp;&nbsp;{data['vehicle_no']}<hr><br/>
                        Driver Mobile&nbsp;&nbsp;:&nbsp;&nbsp;{data['driver_mobile']}<hr><br/>
                        Transporter&nbsp;&nbsp;:&nbsp;&nbsp;{data['transporter']}<hr><br/>
                        Payment Due Date&nbsp;&nbsp;:&nbsp;&nbsp;{data['payment_due']}"""
    # Grid for Details

    address_data = [
        [Paragraph(rec_details, label_style), 
         Paragraph(con_details, label_style), 
         Paragraph(invoice_details, label_style)]
    ]
    
    #address_data = [
    #    [Paragraph("<b>Details of Receiver (Billed To)</b><br/><br/>Pushpa Enterprises<br/>Gala No A/02, Sr No 141, 179<br/>Palhar, Waliv, Vasai<br/>GSTIN: 27BBWPS194BF1ZZ", label_style), 
    #     Paragraph("<b>Details of Consignee (Shipped To)</b><br/><br/>Pushpa Enterprises<br/>Gala No A/02, Sr No 141, 179<br/>Palhar, Waliv, Vasai<br/>GSTIN: 27BBWPS194BF1ZZ", label_style), 
    #     Paragraph("Invoice No: SPC/25-27/0016<br/>Invoice Dt: 15-Apr-26<br/>Order No: 013<br/>Vehicle No: MH46CB7970<br/>Transporter: PARTY KI GADI", label_style)]
    #]

    addr_table = Table(address_data, colWidths=[180, 180, 190])
    addr_table.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    elements.append(addr_table)

    table_data = [[Paragraph("Sr.\nNo.",label_style),Paragraph("Description",label_style),Paragraph("HSN",label_style),Paragraph("GSM",label_style),Paragraph("Thick-\nness",label_style),Paragraph("Size",label_style),Paragraph("No. of\nSheets\nper",label_style),Paragraph("Bundle\nWeight",label_style),Paragraph("Total\nBundle",label_style),Paragraph("Weight",label_style),Paragraph("Rate\n/KG",label_style),Paragraph("Amount",label_style)]]

    srno = 1
    total = 0
    total_bundle = 0
    total_weight = 0

    for item in data["items"]:
        amt = float(item["amount"] or 0)
        total += amt

        bundle = float(item["total_bundle"] or 0)
        total_bundle += bundle

        weight = float(item["weight"] or 0)
        total_weight += weight

        table_data.append([
            srno,
            item["description"],
            item["hsn"],
            item["gsm"],
            item["thickness"],
            item["size"],
            item["sheets"],
            item["bundle_weight"],
            item["total_bundle"],
            item["weight"],
            item["rate"],
            item["amount"]
        ])
        srno = srno + 1

    table_data.append(["","","","","","","","","","",""])
    table_data.append(["Total","","","","","","","",total_bundle,total_weight,"",round(total,2)])

    cgst = round((total * 0.09),2)
    sgst = round((total * 0.09),2)

    net_amount, round_off = calculate_rounding(total + cgst + sgst)


    table = Table(table_data, colWidths=[22, 117, 50, 35, 35, 40, 38, 40, 38, 50, 30, 55]) #550
    table.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('FONTSIZE', (0,0), (-1,-1), 7),
        ('ALIGN', (0,0), (-1,0), 'CENTER'),
        ('VALIGN', (0,0), (-1,0), 'TOP'),
        ('ALIGN', (8,1), (11,-1), 'RIGHT'), # Align numbers to right
        ('BACKGROUND', (0,0), (-1,0), colors.whitesmoke),
        ('SPAN', (0,-1), (7,-1)), # Span total row
    ]))

    elements.append(table)

    # ---------------------------------------------------
    # LEFT SIDE TABLE
    # ---------------------------------------------------

    left_data = [

        [Paragraph("Tax Amount in Word :", label_style),
        Paragraph( amount_to_words_inr(cgst+sgst), label_style)],

        [Paragraph("Net Amount in Word :", label_style),
        Paragraph( amount_to_words_inr(net_amount), label_style)],

        [Paragraph("Bank Details <br/><br/>Bank Name :  HDFC Bank A/c-99903210000000 <br/>Account No :  99903210000000 <br/>IFSC Code  :  HDFC0000145 <br/>Branch        :  Borivali West"), " "]

    ]

    left_table = Table(left_data, colWidths=[80, 300])

    left_table.setStyle(TableStyle([

        ('GRID', (0,0), (-1,-1), 0.5, colors.black),

        ('SPAN', (0,2), (1,2)),

        ('VALIGN', (0,0), (-1,-1), 'TOP'),

        #('LEFTPADDING', (0, 0), (1, 0), 5),
        #('RIGHTPADDING', (0, 0), (1, 0), 5),
        ('TOPPADDING', (0, 0), (1, 1), 10),
        ('BOTTOMPADDING', (0, 0), (1, 1), 10)

        #('LEFTPADDING', (0, 0), (-1, -1), 0),
        #('RIGHTPADDING', (0, 0), (-1, -1), 0),
        #('TOPPADDING', (0, 0), (-1, -1), 0),
        #('BOTTOMPADDING', (0, 0), (-1, -1), 0)

        #('FONTNAME', (0,2), (0,2), 'Helvetica-Bold'),

        #('LINEBEFORE', (1, 0), (1, 1), 0, colors.transparent),

        #('LINEBELOW', (0, 2), (1, -1), 0, colors.transparent)

    ]))

    # ---------------------------------------------------
    # RIGHT SIDE TABLE
    # ---------------------------------------------------

    right_data = [

        ["Taxable Amount", total],
        ["Output CGST", cgst],
        ["Output SGST", sgst],
        ["Rounding Off", round_off],
        ["", ""],
        ["", ""],
        ["", ""],
        ["Net Amount", net_amount],
                
    ]

    right_table = Table(right_data, colWidths=[100, 70])

    right_table.setStyle(TableStyle([

        ('GRID', (0,0), (-1,-1), 0.5, colors.black),

        ('ALIGN', (1,0), (1,-1), 'RIGHT'),

        ('SPAN', (0,4), (1,6)),

        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),

        ('TOPPADDING', (0, 4), (0, 4), 24.20),
        ('BOTTOMPADDING', (0, 4), (0, 4), 24.20),

        ('TOPPADDING', (0, 0), (1, 3), 3.5),
        ('BOTTOMPADDING', (0, 0), (1, 3), 3.5)

        #('FONTNAME', (0,4), (-1,4), 'Helvetica-Bold'),

    ]))

    # ---------------------------------------------------
    # COMBINE BOTH SIDES
    # ---------------------------------------------------

    main_table = Table(
        [[left_table, right_table]],
        colWidths=[380,170]
    )


    main_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0)
    ]))

    inner_data = [
        [Paragraph("For Pushpa Enterprises", styles['Normal'])],
        [Paragraph("Authorised Signatory", styles['Normal'])]
    ]

    # We set a fixed height for this inner table (e.g., 80 points)
    # Row 0 is the top text, Row 1 is the bottom text
    signatory_table = Table(inner_data, colWidths=[170], rowHeights=[15, 65])
    signatory_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (0,0), 'TOP'),    # "For Sunstar..." at the top
        ('VALIGN', (0,1), (0,1), 'BOTTOM'), # "Authorised..." at the bottom
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('LEFTPADDING', (0,0), (0,0), 28),
        ('LEFTPADDING', (0,0), (0,1), 30),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))

    main_data = [
        [
            Paragraph("Terms & Conditions :", styles['Normal']), 
            signatory_table
        ]
    ]

    # Set the height of the main row to match the signatory table (80)
    footer_table = Table(main_data, colWidths=[380, 170], rowHeights=[80])

    footer_table.setStyle(TableStyle([
        # Borders
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        
        # Vertical Alignment for the left side
        ('VALIGN', (0,0), (0,0), 'TOP'), 
        
        # Remove padding so the inner table sits flush against the borders
        ('LEFTPADDING', (0,0), (-1,-1), 5), # Small padding for the label
        ('RIGHTPADDING', (1,0), (1,0), 0),   # 0 padding for the nested table cell
        ('TOPPADDING', (1,0), (1,0), 0),     # 0 padding for the nested table cell
        ('BOTTOMPADDING', (1,0), (1,0), 0),  # 0 padding for the nested table cell
    ]))

    elements.append(main_table)
    elements.append(footer_table)

    doc.build(elements)

@app.post("/invoices")
def create_invoice(data: dict):
    file_id = str(uuid.uuid4())
    filename = f"invoices/{file_id}.pdf"

    generate_pdf(data, filename)

    return {
        "pdf_url": f"http://127.0.0.1:8000/{filename}"
    }