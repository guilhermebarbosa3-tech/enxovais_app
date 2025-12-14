"""Motor de geração de PDF para Não Conformidades (NC)"""
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
from reportlab.lib import colors
from datetime import datetime
import os
import tempfile
from pathlib import Path
from PIL import Image as PILImage

EXPORTS_DIR = Path("exports")
EXPORTS_DIR.mkdir(exist_ok=True)

# Diretório temporário para processamento de fotos
TEMP_DIR = Path(tempfile.gettempdir()) / "enxovais_nc"
TEMP_DIR.mkdir(exist_ok=True)

def generate_nc_pdf(order_row, nc_kind, nc_description, problem_photos):
    """
    Gera PDF de Não Conformidade com fotos do problema.
    
    Args:
        order_row: Dados do pedido (dict)
        nc_kind: Tipo de NC (str)
        nc_description: Descrição do problema (str)
        problem_photos: Lista de caminhos de fotos do problema (list)
    
    Returns:
        Caminho do arquivo PDF gerado (str)
    """
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"nc_pedido_{order_row['id']}_{timestamp}.pdf"
    pdf_path = EXPORTS_DIR / filename
    
    # Criar documento
    doc = SimpleDocTemplate(str(pdf_path), pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    story = []
    
    # Estilos
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#D32F2F'),
        spaceAfter=12,
        alignment=1  # Center
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=colors.HexColor('#D32F2F'),
        spaceAfter=6,
        spaceBefore=6
    )
    
    # Título
    story.append(Paragraph("🚨 RELATÓRIO DE NÃO CONFORMIDADE", title_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Info do Pedido
    story.append(Paragraph("<b>INFORMAÇÕES DO PEDIDO</b>", heading_style))
    
    order_data = [
        ["Pedido #", f"{order_row['id']}"],
        ["Cliente", f"{order_row['client_name']}"],
        ["Categoria", f"{order_row['category']}"],
        ["Tipo", f"{order_row['type']}"],
        ["Produto", f"{order_row['product']}"],
        ["Preço de Venda", f"R$ {order_row['price_sale']:.2f}"],
    ]
    
    order_table = Table(order_data, colWidths=[2*inch, 4*inch])
    order_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F5F5F5')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
    ]))
    
    story.append(order_table)
    story.append(Spacer(1, 0.2*inch))
    
    # Info da NC
    story.append(Paragraph("<b>PROBLEMA ENCONTRADO</b>", heading_style))
    
    nc_data = [
        ["Tipo de NC", f"{nc_kind}"],
        ["Data", f"{datetime.now().strftime('%d/%m/%Y %H:%M')}"],
    ]
    
    nc_table = Table(nc_data, colWidths=[2*inch, 4*inch])
    nc_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#FFF3E0')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
    ]))
    
    story.append(nc_table)
    story.append(Spacer(1, 0.15*inch))
    
    story.append(Paragraph("<b>Descrição:</b>", styles['Normal']))
    story.append(Paragraph(nc_description, styles['Normal']))
    story.append(Spacer(1, 0.2*inch))
    
    # Fotos do Problema
    if problem_photos:
        story.append(Paragraph("<b>FOTOS DO PROBLEMA</b>", heading_style))
        
        photo_elements = []
        for idx, photo_path in enumerate(problem_photos):
            if os.path.exists(photo_path):
                try:
                    # Redimensionar foto para caber no PDF (máx 2 inches)
                    img = PILImage.open(photo_path)
                    max_width = 2.5 * inch
                    max_height = 2.5 * inch
                    img.thumbnail((max_width, max_height), PILImage.Resampling.LANCZOS)
                    
                    # Salvar temporariamente em alta qualidade
                    temp_path = str(TEMP_DIR / f"nc_photo_{idx}.jpg")
                    img.save(temp_path, quality=85)
                    
                    photo_elements.append(Image(temp_path, width=2*inch, height=2*inch))
                    if (idx + 1) % 2 == 0:
                        photo_elements.append(Spacer(1, 0.1*inch))
                except Exception as e:
                    story.append(Paragraph(f"❌ Erro ao carregar foto {idx + 1}: {e}", styles['Normal']))
        
        if photo_elements:
            photos_table = Table([photo_elements[i:i+2] for i in range(0, len(photo_elements), 2)])
            story.append(photos_table)
            story.append(Spacer(1, 0.2*inch))
    
    # Fotos Originais para Comparação
    from core.db import from_json
    original_photos = from_json(order_row['photos'], [])
    
    if original_photos:
        story.append(Paragraph("<b>FOTOS ORIGINAIS (PARA COMPARAÇÃO)</b>", heading_style))
        
        original_elements = []
        for idx, photo_path in enumerate(original_photos):
            if os.path.exists(photo_path):
                try:
                    img = PILImage.open(photo_path)
                    max_width = 2.5 * inch
                    max_height = 2.5 * inch
                    img.thumbnail((max_width, max_height), PILImage.Resampling.LANCZOS)
                    
                    temp_path = str(TEMP_DIR / f"original_photo_{idx}.jpg")
                    img.save(temp_path, quality=85)
                    
                    original_elements.append(Image(temp_path, width=2*inch, height=2*inch))
                    if (idx + 1) % 2 == 0:
                        original_elements.append(Spacer(1, 0.1*inch))
                except Exception as e:
                    story.append(Paragraph(f"❌ Erro ao carregar foto original {idx + 1}: {e}", styles['Normal']))
                    
                    original_elements.append(Image(temp_path, width=2*inch, height=2*inch))
                    if (idx + 1) % 2 == 0:
                        original_elements.append(Spacer(1, 0.1*inch))
                except Exception as e:
                    story.append(Paragraph(f"❌ Erro ao carregar foto original {idx + 1}: {e}", styles['Normal']))
        
        if original_elements:
            original_table = Table([original_elements[i:i+2] for i in range(0, len(original_elements), 2)])
            story.append(original_table)
            story.append(Spacer(1, 0.2*inch))
    
    # Rodapé
    story.append(Spacer(1, 0.3*inch))
    story.append(Paragraph("_" * 80, styles['Normal']))
    story.append(Paragraph(
        f"🧵 ESTOQUE EXONVAIS | Relatório de NC | Gerado em {datetime.now().strftime('%d/%m/%Y às %H:%M')}",
        ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, textColor=colors.grey, alignment=1)
    ))
    
    # Gerar PDF
    doc.build(story)
    
    return str(pdf_path)
