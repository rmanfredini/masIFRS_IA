"""
MAS-IFRS Agent Patch
Intercepta todas as comunicações enviadas/recebidas via SPADE/PEAK
e registra o log estruturado contendo a semântica (RDF/Turtle).
"""

import sys
import os
import logging
from datetime import datetime

# Obter o logger do peak
logger = logging.getLogger("peak.semantic")
logger.setLevel(logging.INFO)

try:
    import spade
    import spade.behaviour
    
    # ─── PATCH: Envio de Mensagens ─────────────────────────────────────────────
    # No SPADE, todos os comportamentos (OneShot, Periodic, etc) herdam de CyclicBehaviour.
    original_send = spade.behaviour.CyclicBehaviour.send
    
    async def patched_send(self, msg, *args, **kwargs):
        try:
            onto = msg.get_metadata("ontology") or "unknown"
            perf = msg.get_metadata("performative") or "unknown"
            thread = msg.thread or "unknown"
            body_content = msg.body or ""
            
            # Codificar quebras de linha no corpo
            escaped_body = body_content.replace("\n", " [NL] ")
            
            # Remetente e destinatário
            sender_jid = str(self.agent.jid) if hasattr(self, "agent") and self.agent else "unknown"
            receiver_jid = str(msg.to)
            
            logger.info(
                f"[SEMANTIC_MSG] SEND | From: {sender_jid} | To: {receiver_jid} | "
                f"Thread: {thread} | Ontology: {onto} | Performative: {perf} | "
                f"Body: {escaped_body}"
            )
            
        except Exception as e:
            logger.error(f"Erro ao logar envio de mensagem semântica: {e}")
            
        return await original_send(self, msg, *args, **kwargs)
        
    spade.behaviour.CyclicBehaviour.send = patched_send
    
    # ─── PATCH: Recebimento de Mensagens ─────────────────────────────────────────
    original_receive = spade.behaviour.CyclicBehaviour.receive
    
    async def patched_receive(self, *args, **kwargs):
        msg = await original_receive(self, *args, **kwargs)
        if msg:
            try:
                onto = msg.get_metadata("ontology") or "unknown"
                perf = msg.get_metadata("performative") or "unknown"
                thread = msg.thread or "unknown"
                body_content = msg.body or ""
                
                escaped_body = body_content.replace("\n", " [NL] ")
                
                receiver_jid = str(self.agent.jid) if hasattr(self, "agent") and self.agent else "unknown"
                sender_jid = str(msg.sender)
                
                logger.info(
                    f"[SEMANTIC_MSG] RECV | From: {sender_jid} | To: {receiver_jid} | "
                    f"Thread: {thread} | Ontology: {onto} | Performative: {perf} | "
                    f"Body: {escaped_body}"
                )
                
            except Exception as e:
                logger.error(f"Erro ao logar recebimento de mensagem semântica: {e}")
        return msg
        
    spade.behaviour.CyclicBehaviour.receive = patched_receive
    
    print("🚀 [MAS-IFRS PATCH] Patch semântico de comunicação aplicado com sucesso no SPADE (via CyclicBehaviour).")
    
except ImportError as e:
    print(f"⚠️ [MAS-IFRS PATCH] Não foi possível aplicar o patch semântico: {e}")
except Exception as e:
    print(f"⚠️ [MAS-IFRS PATCH] Erro ao inicializar o patch: {e}")
