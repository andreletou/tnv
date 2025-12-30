import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone

class SuiviLivraisonConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.livraison_id = self.scope['url_route']['kwargs']['livraison_id']
        self.room_group_name = f'livraison_{self.livraison_id}'

        # Rejoindre le groupe de room
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Quitter le groupe de room
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # Recevoir un message du WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message_type = text_data_json['type']
        
        if message_type == 'position_update':
            # Diffuser la position à tous les clients du groupe
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'position_message',
                    'position': text_data_json['position'],
                    'livreur': text_data_json['livreur']
                }
            )
        elif message_type == 'statut_update':
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'statut_message',
                    'statut': text_data_json['statut']
                }
            )

    # Recevoir un message du groupe
    async def position_message(self, event):
        position = event['position']
        livreur = event['livreur']

        # Envoyer le message au WebSocket
        await self.send(text_data=json.dumps({
            'type': 'position_update',
            'position': position,
            'livreur': livreur,
            'timestamp': timezone.now().isoformat()
        }))

    async def statut_message(self, event):
        statut = event['statut']

        await self.send(text_data=json.dumps({
            'type': 'statut_update',
            'statut': statut,
            'timestamp': timezone.now().isoformat()
        }))