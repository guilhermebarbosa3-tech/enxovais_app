"""Motor de geração de PDF com fotos para pedidos."""
import os
from datetime import datetime
from io import BytesIO
from PIL import Image
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor, grey
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, Table, TableStyle, PageBreak
from reportlab.lib import colors
from core.db import from_json


def generate_order_pdf(order_row, photos_paths: list = None) -> str:
    """
    Gera PDF completo do pedido com fotos embutidas.
    
    Args:
        order_row: dict com dados do pedido (de database)
        photos_paths: lista de caminhos das fotos
    
    Returns:
        str: caminho do arquivo PDF gerado
    """
    
    if photos_paths is None:
        photos_paths = from_json(order_row['photos'], [])
    
    # Criar diretório de exports
    exports_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "exports"))
    os.makedirs(exports_dir, exist_ok=True)
    
    # Nome do arquivo
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"pedido_{order_row['id']}_{timestamp}.pdf"
    filepath = os.path.join(exports_dir, filename)
    
    # Criar documento PDF
    doc = SimpleDocTemplate(filepath, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
    story = []
    styles = getSampleStyleSheet()
    
    # Estilos customizados
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=HexColor('#2C3E50'),
        spaceAfter=6,
        alignment=1  # center
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=HexColor('#34495E'),
        spaceAfter=6,
        spaceBefore=12,
        borderPadding=5
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=4
    )
    
    # Header
    story.append(Paragraph("🧵 ESTOQUE EXONVAIS", title_style))
    story.append(Paragraph(f"PEDIDO #{order_row['id']}", heading_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Dados básicos
    data = [
        ['Data:', datetime.fromisoformat(order_row['created_at']).strftime("%d/%m/%Y %H:%M")],
        ['Cliente:', order_row['client_name']],
        ['Status:', order_row['status']],
    ]
    table = Table(data, colWidths=[1.5*inch, 4*inch])
    table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), HexColor('#34495E')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(table)
    story.append(Spacer(1, 0.2*inch))
    
    # Produto
    story.append(Paragraph("PRODUTO", heading_style))
    data = [
        ['Categoria:', order_row['category']],
        ['Tipo:', order_row['type']],
        ['Produto:', order_row['product']],
    ]
    table = Table(data, colWidths=[1.5*inch, 4*inch])
    table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(table)
    story.append(Spacer(1, 0.2*inch))
    
    # Preços
    story.append(Paragraph("PREÇOS", heading_style))
    margin = order_row['price_sale'] - order_row['price_cost']
    data = [
        ['Custo:', f"R$ {order_row['price_cost']:.2f}"],
        ['Venda:', f"R$ {order_row['price_sale']:.2f}"],
        ['Margem:', f"R$ {margin:.2f}"],
    ]
    table = Table(data, colWidths=[1.5*inch, 4*inch])
    table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(table)
    story.append(Spacer(1, 0.2*inch))
    
    # Especificações
    notes_struct = from_json(order_row['notes_struct'], {})
    if notes_struct:
        story.append(Paragraph("ESPECIFICAÇÕES", heading_style))
        for key, value in notes_struct.items():
            story.append(Paragraph(f"<b>{key.upper()}:</b> {value}", normal_style))
        story.append(Spacer(1, 0.2*inch))
    
    # Observações
    if order_row['notes_free']:
        story.append(Paragraph("OBSERVAÇÕES", heading_style))
        story.append(Paragraph(order_row['notes_free'], normal_style))
        story.append(Spacer(1, 0.2*inch))
    
    # Fotos
    if photos_paths:
        story.append(Paragraph("FOTOS DO PEDIDO", heading_style))
        story.append(Spacer(1, 0.1*inch))
        
        # Grid de fotos 3x3
        photo_data = []
        photo_row = []
        
        for idx, photo_path in enumerate(photos_paths):
            try:
                # Abrir imagem e redimensionar
                img = Image.open(photo_path)
                # Redimensionar para max 1.5 inch
                img.thumbnail((1.5*inch, 1.5*inch), Image.Resampling.LANCZOS)
                
                # Salvar em BytesIO para reportlab
                img_io = BytesIO()
                img.save(img_io, format='JPEG', quality=85)
                img_io.seek(0)
                
                # Criar imagem reportlab
                rl_img = RLImage(img_io, width=1.4*inch, height=1.4*inch)
                photo_row.append(rl_img)
                
                # Nova linha a cada 3 fotos
                if (idx + 1) % 3 == 0:
                    photo_data.append(photo_row)
                    photo_row = []
            except Exception as e:
                print(f"Erro ao processar foto {photo_path}: {e}")
        
        # Adicionar última linha se não completa
        if photo_row:
            # Preencher com células vazias se < 3
            while len(photo_row) < 3:
                photo_row.append(Spacer(1.4*inch, 1.4*inch))
            photo_data.append(photo_row)
        
        if photo_data:
            photo_table = Table(photo_data, colWidths=[1.5*inch, 1.5*inch, 1.5*inch])
            photo_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 5),
                ('RIGHTPADDING', (0, 0), (-1, -1), 5),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ]))
            story.append(photo_table)
    
    # Footer
    story.append(Spacer(1, 0.3*inch))
    footer_text = f"Gerado em {datetime.now().strftime('%d/%m/%Y às %H:%M')} | Estoque Exonvais"
    story.append(Paragraph(f"<i>{footer_text}</i>", ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=grey,
        alignment=1
    )))
    
    # Gerar PDF
    doc.build(story)
    
    return filepath
