"""
Export service for generating PDF and CSV exports
"""
import csv
import io
from typing import List, Dict, Any
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from app.logging_config import logger


class ExportService:
    """Service for exporting ideas to various formats"""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
    
    def export_to_csv(self, ideas: List[Dict[str, Any]]) -> str:
        """
        Export ideas to CSV format
        
        Args:
            ideas: List of idea dictionaries
            
        Returns:
            CSV content as string
        """
        output = io.StringIO()
        
        if not ideas:
            return ""
        
        fieldnames = [
            'idea_text', 'score_market', 'score_tech', 'score_competition',
            'score_monetisation', 'score_feasibility', 'score_overall',
            'complaint_content', 'complaint_source', 'generated_at'
        ]
        
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        for idea in ideas:
            row = {
                'idea_text': idea.get('idea_text', ''),
                'score_market': idea.get('score_market', 0),
                'score_tech': idea.get('score_tech', 0),
                'score_competition': idea.get('score_competition', 0),
                'score_monetisation': idea.get('score_monetisation', 0),
                'score_feasibility': idea.get('score_feasibility', 0),
                'score_overall': idea.get('score_overall', 0),
                'complaint_content': idea.get('complaint', {}).get('content', ''),
                'complaint_source': idea.get('complaint', {}).get('source', ''),
                'generated_at': idea.get('generated_at', '')
            }
            writer.writerow(row)
        
        csv_content = output.getvalue()
        output.close()
        
        logger.info(f"Exported {len(ideas)} ideas to CSV")
        return csv_content
    
    def export_to_pdf(self, ideas: List[Dict[str, Any]]) -> bytes:
        """
        Export ideas to PDF format
        
        Args:
            ideas: List of idea dictionaries
            
        Returns:
            PDF content as bytes
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        
        story = []
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            textColor=colors.blue
        )
        story.append(Paragraph("App Idea Hunter - Generated Ideas", title_style))
        story.append(Spacer(1, 20))
        
        if not ideas:
            story.append(Paragraph("No ideas to export.", self.styles['Normal']))
        else:
            for i, idea in enumerate(ideas, 1):
                # Idea header
                idea_title = f"Idea #{i}: {idea.get('idea_text', 'Untitled')}"
                story.append(Paragraph(idea_title, self.styles['Heading2']))
                
                # Scores table
                scores_data = [
                    ['Market', 'Tech', 'Competition', 'Monetization', 'Feasibility', 'Overall'],
                    [
                        str(idea.get('score_market', 0)),
                        str(idea.get('score_tech', 0)),
                        str(idea.get('score_competition', 0)),
                        str(idea.get('score_monetisation', 0)),
                        str(idea.get('score_feasibility', 0)),
                        str(idea.get('score_overall', 0))
                    ]
                ]
                
                scores_table = Table(scores_data)
                scores_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 14),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                
                story.append(scores_table)
                story.append(Spacer(1, 12))
                
                # Original complaint
                complaint = idea.get('complaint', {})
                if complaint.get('content'):
                    story.append(Paragraph("<b>Original Complaint:</b>", self.styles['Normal']))
                    complaint_text = complaint['content'][:500] + "..." if len(complaint['content']) > 500 else complaint['content']
                    story.append(Paragraph(complaint_text, self.styles['Normal']))
                    
                    source = complaint.get('source', 'Unknown')
                    story.append(Paragraph(f"<b>Source:</b> {source}", self.styles['Normal']))
                
                story.append(Spacer(1, 20))
                
                # Page break after every 3 ideas
                if i % 3 == 0 and i < len(ideas):
                    story.append(Spacer(1, 50))
        
        doc.build(story)
        pdf_content = buffer.getvalue()
        buffer.close()
        
        logger.info(f"Exported {len(ideas)} ideas to PDF")
        return pdf_content