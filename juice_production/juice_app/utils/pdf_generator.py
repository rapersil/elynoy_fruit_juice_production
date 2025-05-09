from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from decimal import Decimal
from django.utils import timezone

def generate_sale_receipt_pdf(sale, payments=None):
    """Generate a PDF receipt for a sale."""
    buffer = BytesIO()
    
    # Create the PDF object
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    
    # Create custom styles
    styles.add(ParagraphStyle(name='Center', alignment=1))
    styles.add(ParagraphStyle(name='Right', alignment=2))
    styles.add(ParagraphStyle(name='Title', fontSize=16, spaceAfter=12, alignment=1))
    styles.add(ParagraphStyle(name='Subtitle', fontSize=14, spaceAfter=10, alignment=1))
    
    # Create the content elements
    elements = []
    
    # Company information
    elements.append(Paragraph("Fruit Juice Production Ltd", styles['Title']))
    elements.append(Paragraph("123 Production Lane, Accra, Ghana", styles['Center']))
    elements.append(Paragraph("Phone: +233 12 345 6789 | Email: info@fruitjuice.com", styles['Center']))
    elements.append(Spacer(1, 0.2*inch))
    
    # Receipt title
    elements.append(Paragraph("RECEIPT", styles['Subtitle']))
    elements.append(Spacer(1, 0.2*inch))
    
    # Customer and sale information
    data = [
        ["Invoice Number:", sale.invoice_number],
        ["Date:", sale.sale_date.strftime("%d %b, %Y")],
        ["Customer:", sale.customer.name],
        ["Contact:", sale.customer.phone],
        ["Status:", sale.status.upper()],
        ["Payment Status:", sale.payment_status.upper()],
    ]
    
    sale_info_table = Table(data, colWidths=[2*inch, 3.5*inch])
    sale_info_table.setStyle(TableStyle([
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (0,0), (0,-1), 'RIGHT'),
        ('ALIGN', (1,0), (1,-1), 'LEFT'),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(sale_info_table)
    elements.append(Spacer(1, 0.2*inch))
    
    # Items table
    items = sale.items.all()
    item_data = [["Product", "Description", "Qty", "Unit Price", "Total"]]
    
    for item in items:
        item_data.append([
            item.product.name,
            item.product.description[:30] + "..." if len(item.product.description) > 30 else item.product.description,
            str(item.quantity),
            f"GHS{item.unit_price:.2f}",
            f"GHS{item.total_price:.2f}"
        ])
    
    # Subtotal, tax and total
    subtotal = sum(item.total_price for item in items)
    tax_rate = Decimal('0.05')  # 5% VAT
    tax_amount = subtotal * tax_rate
    total = subtotal + tax_amount
    
    item_data.append(["", "", "", "Subtotal:", f"GHS{subtotal:.2f}"])
    item_data.append(["", "", "", f"VAT ({int(tax_rate * 100)}%):", f"GHS{tax_amount:.2f}"])
    item_data.append(["", "", "", "Total:", f"GHS{total:.2f}"])
    
    # Create the items table
    item_table = Table(item_data, colWidths=[1.8*inch, 2.2*inch, 0.6*inch, 1.2*inch, 1.2*inch])
    item_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('TEXTCOLOR', (0,0), (-1,0), colors.black),
        ('ALIGN', (0,0), (-1,0), 'CENTER'),
        ('FONTSIZE', (0,0), (-1,0), 10),
        ('BOTTOMPADDING', (0,0), (-1,0), 8),
        ('BACKGROUND', (0,1), (-1,-4), colors.white),
        ('GRID', (0,0), (-1,-4), 0.5, colors.grey),
        ('ALIGN', (2,1), (2,-4), 'CENTER'),
        ('ALIGN', (3,1), (4,-1), 'RIGHT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('FONTSIZE', (0,1), (-1,-1), 9),
        ('TOPPADDING', (0,1), (-1,-1), 6),
        ('BOTTOMPADDING', (0,1), (-1,-1), 6),
        ('BACKGROUND', (0,-3), (-1,-1), colors.lightgrey),
        ('GRID', (3,-3), (-1,-1), 0.5, colors.grey),
        ('FONTSIZE', (3,-1), (4,-1), 10),
        ('FONTSIZE', (3,-3), (4,-3), 9),
        ('FONTSIZE', (3,-2), (4,-2), 9),
    ]))
    elements.append(item_table)
    
    # Payment information if provided
    if payments:
        elements.append(Spacer(1, 0.3*inch))
        elements.append(Paragraph("Payment Information", styles['Subtitle']))
        
        payment_data = [["Date", "Amount", "Method", "Reference"]]
        total_paid = Decimal('0.00')
        
        for payment in payments:
            payment_data.append([
                payment.payment_date.strftime("%d %b, %Y"),
                f"GHS{payment.amount:.2f}",
                payment.get_payment_method_display(),
                payment.reference_number or "-"
            ])
            total_paid += payment.amount
        
        balance = sale.total_amount - total_paid
        payment_data.append(["", "", "Total Paid:", f"GHS{total_paid:.2f}"])
        payment_data.append(["", "", "Balance:", f"GHS{balance:.2f}"])
        
        payment_table = Table(payment_data, colWidths=[1.3*inch, 1.2*inch, 1.5*inch, 3*inch])
        payment_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
            ('TEXTCOLOR', (0,0), (-1,0), colors.black),
            ('ALIGN', (0,0), (-1,0), 'CENTER'),
            ('FONTSIZE', (0,0), (-1,0), 10),
            ('BOTTOMPADDING', (0,0), (-1,0), 8),
            ('BACKGROUND', (0,1), (-1,-3), colors.white),
            ('GRID', (0,0), (-1,-3), 0.5, colors.grey),
            ('ALIGN', (1,1), (1,-3), 'RIGHT'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('FONTSIZE', (0,1), (-1,-1), 9),
            ('TOPPADDING', (0,1), (-1,-1), 6),
            ('BOTTOMPADDING', (0,1), (-1,-1), 6),
            ('BACKGROUND', (0,-2), (-1,-1), colors.lightgrey),
            ('GRID', (2,-2), (-1,-1), 0.5, colors.grey),
            ('ALIGN', (2,-2), (3,-1), 'RIGHT'),
            ('FONTSIZE', (2,-2), (3,-1), 9),
        ]))
        elements.append(payment_table)
    
    # Footer
    elements.append(Spacer(1, 0.3*inch))
    elements.append(Paragraph("Thank you for your business!", styles['Center']))
    elements.append(Paragraph(f"This receipt was generated on {timezone.now().strftime('%d %b, %Y at %H:%M')}", styles['Center']))
    
    # Build the PDF
    doc.build(elements)
    
    # Get the PDF content
    pdf = buffer.getvalue()
    buffer.close()
    
    return pdf

def generate_sales_report_pdf(start_date, end_date, sales, summary_data):
    """Generate a PDF sales report."""
    buffer = BytesIO()
    
    # Create the PDF object
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    
    # Create custom styles
    styles.add(ParagraphStyle(name='Center', alignment=1))
    styles.add(ParagraphStyle(name='Right', alignment=2))
    styles.add(ParagraphStyle(name='Title', fontSize=16, spaceAfter=12, alignment=1))
    styles.add(ParagraphStyle(name='Subtitle', fontSize=14, spaceAfter=10, alignment=1))
    
    # Create the content elements
    elements = []
    
    # Company information and report title
    elements.append(Paragraph("Fruit Juice Production Ltd", styles['Title']))
    elements.append(Paragraph("Sales Report", styles['Subtitle']))
    elements.append(Paragraph(f"Period: {start_date.strftime('%d %b, %Y')} to {end_date.strftime('%d %b, %Y')}", styles['Center']))
    elements.append(Spacer(1, 0.3*inch))
    
    # Summary statistics
    elements.append(Paragraph("Summary", styles['Subtitle']))
    
    summary_data = [
        ["Total Sales:", f"GHS{summary_data['total_sales']:.2f}"],
        ["Number of Sales:", str(summary_data['total_count'])],
        ["Average Sale Value:", f"GHS{summary_data['avg_sale']:.2f}"],
        ["Total Products Sold:", str(summary_data['total_products_sold'])],
    ]
    
    summary_table = Table(summary_data, colWidths=[2*inch, 3*inch])
    summary_table.setStyle(TableStyle([
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (0,0), (0,-1), 'RIGHT'),
        ('ALIGN', (1,0), (1,-1), 'LEFT'),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 0.2*inch))
    
    # Sales by status
    if 'sales_by_status' in summary_data:
        elements.append(Paragraph("Sales by Status", styles['Subtitle']))
        
        status_data = [["Status", "Count", "Total"]]
        for status in summary_data['sales_by_status']:
            status_data.append([
                status['status'].title(),
                str(status['count']),
                f"GHS{status['total']:.2f}"
            ])
        
        status_table = Table(status_data, colWidths=[2*inch, 1.5*inch, 3*inch])
        status_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
            ('TEXTCOLOR', (0,0), (-1,0), colors.black),
            ('ALIGN', (0,0), (-1,0), 'CENTER'),
            ('FONTSIZE', (0,0), (-1,0), 10),
            ('BOTTOMPADDING', (0,0), (-1,0), 8),
            ('BACKGROUND', (0,1), (-1,-1), colors.white),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('ALIGN', (1,1), (1,-1), 'CENTER'),
            ('ALIGN', (2,1), (2,-1), 'RIGHT'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('FONTSIZE', (0,1), (-1,-1), 9),
            ('TOPPADDING', (0,1), (-1,-1), 6),
            ('BOTTOMPADDING', (0,1), (-1,-1), 6),
        ]))
        elements.append(status_table)
        elements.append(Spacer(1, 0.2*inch))
    
    # Top products
    if 'top_products' in summary_data:
        elements.append(Paragraph("Top Products", styles['Subtitle']))
        
        product_data = [["Product", "Quantity", "Revenue", "Avg. Price"]]
        for product in summary_data['top_products'][:10]:  # Limit to top 10
            product_data.append([
                product['product__name'],
                str(product['quantity']),
                f"GHS{product['revenue']:.2f}",
                f"GHS{product['avg_price']:.2f}"
            ])
        
        product_table = Table(product_data, colWidths=[3*inch, 1*inch, 1.5*inch, 1.5*inch])
        product_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
            ('TEXTCOLOR', (0,0), (-1,0), colors.black),
            ('ALIGN', (0,0), (-1,0), 'CENTER'),
            ('FONTSIZE', (0,0), (-1,0), 10),
            ('BOTTOMPADDING', (0,0), (-1,0), 8),
            ('BACKGROUND', (0,1), (-1,-1), colors.white),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('ALIGN', (1,1), (1,-1), 'CENTER'),
            ('ALIGN', (2,1), (3,-1), 'RIGHT'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('FONTSIZE', (0,1), (-1,-1), 9),
            ('TOPPADDING', (0,1), (-1,-1), 6),
            ('BOTTOMPADDING', (0,1), (-1,-1), 6),
        ]))
        elements.append(product_table)
        elements.append(Spacer(1, 0.2*inch))
    
    # Sales list
    elements.append(Paragraph("Sales List", styles['Subtitle']))
    
    sales_data = [["Invoice #", "Date", "Customer", "Amount", "Status", "Payment"]]
    for sale in sales:
        sales_data.append([
            sale.invoice_number,
            sale.sale_date.strftime("%d %b, %Y"),
            sale.customer.name[:25] + "..." if len(sale.customer.name) > 25 else sale.customer.name,
            f"GHS{sale.total_amount:.2f}",
            sale.status.title(),
            sale.payment_status.title()
        ])
    
    sales_table = Table(sales_data, colWidths=[1.3*inch, 1*inch, 2.5*inch, 1*inch, 1*inch, 1*inch])
    sales_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('TEXTCOLOR', (0,0), (-1,0), colors.black),
        ('ALIGN', (0,0), (-1,0), 'CENTER'),
        ('FONTSIZE', (0,0), (-1,0), 10),
        ('BOTTOMPADDING', (0,0), (-1,0), 8),
        ('BACKGROUND', (0,1), (-1,-1), colors.white),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('ALIGN', (3,1), (3,-1), 'RIGHT'),
        ('ALIGN', (4,1), (5,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('FONTSIZE', (0,1), (-1,-1), 8),
        ('TOPPADDING', (0,1), (-1,-1), 6),
        ('BOTTOMPADDING', (0,1), (-1,-1), 6),
    ]))
    elements.append(sales_table)
    
    # Footer
    elements.append(Spacer(1, 0.3*inch))
    elements.append(Paragraph(f"Report generated on {timezone.now().strftime('%d %b, %Y at %H:%M')}", styles['Right']))
    
    # Build the PDF
    doc.build(elements)
    
    # Get the PDF content
    pdf = buffer.getvalue()
    buffer.close()
    
    return pdf