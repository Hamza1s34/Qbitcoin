#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Modal Dialogs for Qbitcoin GUI Application
Contains all modal dialog implementations for displaying detailed information
"""

import flet as ft
import datetime
from pyqrllib.pyqrllib import bin2hstr


class BlockDetailsModal:
    """Modal dialog for displaying detailed block information"""
    
    def __init__(self, page: ft.Page):
        self.page = page
        
    def show(self, block_info, on_close=None):
        """Show block details modal"""
        try:
            # Extract block data
            block_number = block_info.header.block_number
            block_hash = bin2hstr(block_info.header.hash_header)
            timestamp = block_info.header.timestamp_seconds
            tx_count = len(block_info.transactions)
            block_size = len(block_info.SerializeToString())
            prev_hash = bin2hstr(block_info.header.hash_header_prev) if block_info.header.hash_header_prev else "N/A"
            merkle_root = bin2hstr(block_info.header.merkle_root) if block_info.header.merkle_root else "N/A"
            nonce = block_info.header.nonce if hasattr(block_info.header, 'nonce') else "N/A"
            difficulty = block_info.header.block_reward if hasattr(block_info.header, 'block_reward') else "N/A"
            
            # Convert timestamp to readable format
            readable_time = datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S UTC')
            
            # Create transaction list
            tx_rows = []
            for i, tx in enumerate(block_info.transactions):
                tx_hash = bin2hstr(tx.transaction_hash) if tx.transaction_hash else f"TX_{i}"
                tx_type = getattr(tx, 'type', 'Unknown')
                tx_fee = getattr(tx, 'fee', 0)
                
                tx_rows.append(
                    ft.DataRow(
                        cells=[
                            ft.DataCell(ft.Text(str(i))),
                            ft.DataCell(ft.Text(f"{tx_hash[:16]}..." if len(tx_hash) > 16 else tx_hash)),
                            ft.DataCell(ft.Text(str(tx_type))),
                            ft.DataCell(ft.Text(f"{tx_fee:,}")),
                            ft.DataCell(ft.ElevatedButton("View", 
                                       on_click=lambda e, tx=tx: self.show_transaction_details(tx)))
                        ]
                    )
                )
            
            # Create modal content
            modal_content = ft.Container(
                content=ft.Column([
                    # Header
                    ft.Row([
                        ft.Text("Block Details", size=24, weight=ft.FontWeight.BOLD),
                        ft.IconButton(ft.Icons.CLOSE, on_click=lambda e: self.close_modal())
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    
                    ft.Divider(),
                    
                    # Block info
                    ft.Container(
                        content=ft.Column([
                            ft.Text("Block Information", size=18, weight=ft.FontWeight.BOLD),
                            
                            # Basic info grid
                            ft.Row([
                                ft.Container(
                                    content=ft.Column([
                                        ft.Text("Block Number", weight=ft.FontWeight.BOLD),
                                        ft.Text(str(block_number) + (" (Genesis)" if block_number == 0 else "")),
                                        
                                        ft.Text("Timestamp", weight=ft.FontWeight.BOLD),
                                        ft.Text(readable_time),
                                        
                                        ft.Text("Transactions", weight=ft.FontWeight.BOLD),
                                        ft.Text(str(tx_count)),
                                        
                                        ft.Text("Block Size", weight=ft.FontWeight.BOLD),
                                        ft.Text(f"{block_size:,} bytes"),
                                    ], spacing=5),
                                    width=200
                                ),
                                ft.Container(
                                    content=ft.Column([
                                        ft.Text("Block Hash", weight=ft.FontWeight.BOLD),
                                        ft.SelectionArea(content=ft.Text(block_hash, selectable=True)),
                                        
                                        ft.Text("Previous Hash", weight=ft.FontWeight.BOLD),
                                        ft.SelectionArea(content=ft.Text(prev_hash, selectable=True)),
                                        
                                        ft.Text("Merkle Root", weight=ft.FontWeight.BOLD),
                                        ft.SelectionArea(content=ft.Text(merkle_root, selectable=True)),
                                        
                                        ft.Text("Nonce", weight=ft.FontWeight.BOLD),
                                        ft.Text(str(nonce)),
                                    ], spacing=5),
                                    expand=True
                                )
                            ], spacing=20)
                        ]),
                        bgcolor=ft.Colors.GREY_800,
                        padding=15,
                        border_radius=10
                    ),
                    
                    # Transactions section
                    ft.Container(
                        content=ft.Column([
                            ft.Text("Transactions", size=18, weight=ft.FontWeight.BOLD),
                            ft.DataTable(
                                columns=[
                                    ft.DataColumn(ft.Text("#")),
                                    ft.DataColumn(ft.Text("Transaction Hash")),
                                    ft.DataColumn(ft.Text("Type")),
                                    ft.DataColumn(ft.Text("Fee")),
                                    ft.DataColumn(ft.Text("Actions"))
                                ],
                                rows=tx_rows
                            )
                        ]),
                        bgcolor=ft.Colors.GREY_800,
                        padding=15,
                        border_radius=10,
                        height=300
                    )
                ], 
                spacing=15,
                scroll=ft.ScrollMode.AUTO),
                width=900,
                height=700,
                bgcolor=ft.Colors.GREY_900,
                padding=20,
                border_radius=15
            )
            
            # Create and show modal
            self.modal = ft.AlertDialog(
                modal=True,
                content=modal_content,
                content_padding=0
            )
            
            self.page.dialog = self.modal
            self.modal.open = True
            self.page.update()
            
        except Exception as ex:
            self.show_error_dialog(f"Error displaying block details: {str(ex)}")
    
    def show_transaction_details(self, tx):
        """Show transaction details modal"""
        TransactionDetailsModal(self.page).show(tx)
    
    def close_modal(self):
        """Close the modal"""
        if hasattr(self, 'modal'):
            self.modal.open = False
            self.page.update()
    
    def show_error_dialog(self, message):
        """Show error dialog"""
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Error"),
            content=ft.Text(message),
            actions=[ft.TextButton("OK", on_click=lambda e: self.close_error_dialog(dialog))]
        )
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()
    
    def close_error_dialog(self, dialog):
        """Close error dialog"""
        dialog.open = False
        self.page.update()


class TransactionDetailsModal:
    """Modal dialog for displaying detailed transaction information"""
    
    def __init__(self, page: ft.Page):
        self.page = page
        
    def show(self, tx, on_close=None):
        """Show transaction details modal"""
        try:
            # Extract transaction data
            tx_hash = bin2hstr(tx.transaction_hash) if tx.transaction_hash else "N/A"
            tx_type = getattr(tx, 'type', 'Unknown')
            tx_fee = getattr(tx, 'fee', 0)
            tx_nonce = getattr(tx, 'nonce', 'N/A')
            
            # Get transaction specific data based on type
            from_addr = "N/A"
            to_addr = "N/A"
            amount = 0
            
            # Try to extract addresses and amount based on transaction structure
            if hasattr(tx, 'transfer') and tx.transfer:
                from_addr = bin2hstr(tx.addr_from) if hasattr(tx, 'addr_from') and tx.addr_from else "N/A"
                to_addr = bin2hstr(tx.transfer.addr_to) if tx.transfer.addr_to else "N/A"
                amount = tx.transfer.amount if hasattr(tx.transfer, 'amount') else 0
            elif hasattr(tx, 'addr_from'):
                from_addr = bin2hstr(tx.addr_from) if tx.addr_from else "N/A"
            
            # Create modal content
            modal_content = ft.Container(
                content=ft.Column([
                    # Header
                    ft.Row([
                        ft.Text("Transaction Details", size=24, weight=ft.FontWeight.BOLD),
                        ft.IconButton(ft.Icons.CLOSE, on_click=lambda e: self.close_modal())
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    
                    ft.Divider(),
                    
                    # Transaction info
                    ft.Container(
                        content=ft.Column([
                            ft.Text("Transaction Information", size=18, weight=ft.FontWeight.BOLD),
                            
                            ft.Row([
                                ft.Text("Transaction Hash:", weight=ft.FontWeight.BOLD),
                                ft.SelectionArea(content=ft.Text(tx_hash, selectable=True))
                            ]),
                            
                            ft.Row([
                                ft.Text("Type:", weight=ft.FontWeight.BOLD),
                                ft.Text(str(tx_type))
                            ]),
                            
                            ft.Row([
                                ft.Text("Fee:", weight=ft.FontWeight.BOLD),
                                ft.Text(f"{tx_fee:,} Qbit")
                            ]),
                            
                            ft.Row([
                                ft.Text("Nonce:", weight=ft.FontWeight.BOLD),
                                ft.Text(str(tx_nonce))
                            ]),
                            
                            ft.Row([
                                ft.Text("From Address:", weight=ft.FontWeight.BOLD),
                                ft.SelectionArea(content=ft.Text(from_addr, selectable=True))
                            ]),
                            
                            ft.Row([
                                ft.Text("To Address:", weight=ft.FontWeight.BOLD),
                                ft.SelectionArea(content=ft.Text(to_addr, selectable=True))
                            ]),
                            
                            ft.Row([
                                ft.Text("Amount:", weight=ft.FontWeight.BOLD),
                                ft.Text(f"{amount:,} Qbit")
                            ]),
                        ], spacing=10),
                        bgcolor=ft.Colors.GREY_800,
                        padding=15,
                        border_radius=10
                    )
                ], spacing=15),
                width=600,
                height=400,
                bgcolor=ft.Colors.GREY_900,
                padding=20,
                border_radius=15
            )
            
            # Create and show modal
            self.modal = ft.AlertDialog(
                modal=True,
                content=modal_content,
                content_padding=0
            )
            
            self.page.dialog = self.modal
            self.modal.open = True
            self.page.update()
            
        except Exception as ex:
            self.show_error_dialog(f"Error displaying transaction details: {str(ex)}")
    
    def close_modal(self):
        """Close the modal"""
        if hasattr(self, 'modal'):
            self.modal.open = False
            self.page.update()
    
    def show_error_dialog(self, message):
        """Show error dialog"""
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Error"),
            content=ft.Text(message),
            actions=[ft.TextButton("OK", on_click=lambda e: self.close_error_dialog(dialog))]
        )
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()
    
    def close_error_dialog(self, dialog):
        """Close error dialog"""
        dialog.open = False
        self.page.update()


class WalletDetailsModal:
    """Modal dialog for displaying detailed wallet information"""
    
    def __init__(self, page: ft.Page):
        self.page = page
        
    def show(self, wallet_info, on_close=None):
        """Show wallet details modal"""
        try:
            # Create modal content
            modal_content = ft.Container(
                content=ft.Column([
                    # Header
                    ft.Row([
                        ft.Text("Wallet Details", size=24, weight=ft.FontWeight.BOLD),
                        ft.IconButton(ft.Icons.CLOSE, on_click=lambda e: self.close_modal())
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    
                    ft.Divider(),
                    
                    # Wallet info
                    ft.Container(
                        content=ft.Column([
                            ft.Text("Wallet Information", size=18, weight=ft.FontWeight.BOLD),
                            
                            ft.Row([
                                ft.Text("Wallet Version:", weight=ft.FontWeight.BOLD),
                                ft.Text(str(getattr(wallet_info, 'version', 'N/A')))
                            ]),
                            
                            ft.Row([
                                ft.Text("Address Count:", weight=ft.FontWeight.BOLD),
                                ft.Text(str(getattr(wallet_info, 'address_count', 'N/A')))
                            ]),
                            
                            ft.Row([
                                ft.Text("Is Encrypted:", weight=ft.FontWeight.BOLD),
                                ft.Text("Yes" if getattr(wallet_info, 'is_encrypted', False) else "No")
                            ]),
                        ], spacing=10),
                        bgcolor=ft.Colors.GREY_800,
                        padding=15,
                        border_radius=10
                    )
                ], spacing=15),
                width=500,
                height=300,
                bgcolor=ft.Colors.GREY_900,
                padding=20,
                border_radius=15
            )
            
            # Create and show modal
            self.modal = ft.AlertDialog(
                modal=True,
                content=modal_content,
                content_padding=0
            )
            
            self.page.dialog = self.modal
            self.modal.open = True
            self.page.update()
            
        except Exception as ex:
            self.show_error_dialog(f"Error displaying wallet details: {str(ex)}")
    
    def close_modal(self):
        """Close the modal"""
        if hasattr(self, 'modal'):
            self.modal.open = False
            self.page.update()
    
    def show_error_dialog(self, message):
        """Show error dialog"""
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Error"),
            content=ft.Text(message),
            actions=[ft.TextButton("OK", on_click=lambda e: self.close_error_dialog(dialog))]
        )
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()
    
    def close_error_dialog(self, dialog):
        """Close error dialog"""
        dialog.open = False
        self.page.update()


class SearchModal:
    """Modal dialog for advanced search functionality"""
    
    def __init__(self, page: ft.Page, gui_instance):
        self.page = page
        self.gui = gui_instance
        
    def show(self, on_close=None):
        """Show search modal"""
        try:
            # Search type dropdown
            self.search_type = ft.Dropdown(
                label="Search Type",
                width=200,
                options=[
                    ft.dropdown.Option("block_number", "Block Number"),
                    ft.dropdown.Option("block_hash", "Block Hash"),
                    ft.dropdown.Option("transaction_hash", "Transaction Hash"),
                    ft.dropdown.Option("address", "Address"),
                ],
                value="block_number"
            )
            
            # Search input
            self.search_input = ft.TextField(
                label="Enter search term",
                width=400,
                autofocus=True
            )
            
            # Create modal content
            modal_content = ft.Container(
                content=ft.Column([
                    # Header
                    ft.Row([
                        ft.Text("Advanced Search", size=24, weight=ft.FontWeight.BOLD),
                        ft.IconButton(ft.Icons.CLOSE, on_click=lambda e: self.close_modal())
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    
                    ft.Divider(),
                    
                    # Search form
                    ft.Container(
                        content=ft.Column([
                            ft.Text("Search the Blockchain", size=18, weight=ft.FontWeight.BOLD),
                            
                            ft.Row([
                                self.search_type,
                                self.search_input
                            ], spacing=15),
                            
                            ft.Row([
                                ft.ElevatedButton(
                                    "Search",
                                    icon=ft.Icons.SEARCH,
                                    on_click=self.perform_search
                                ),
                                ft.TextButton(
                                    "Cancel",
                                    on_click=lambda e: self.close_modal()
                                )
                            ], spacing=10)
                        ], spacing=15),
                        bgcolor=ft.Colors.GREY_800,
                        padding=15,
                        border_radius=10
                    )
                ], spacing=15),
                width=500,
                height=300,
                bgcolor=ft.Colors.GREY_900,
                padding=20,
                border_radius=15
            )
            
            # Create and show modal
            self.modal = ft.AlertDialog(
                modal=True,
                content=modal_content,
                content_padding=0
            )
            
            self.page.dialog = self.modal
            self.modal.open = True
            self.page.update()
            
        except Exception as ex:
            self.show_error_dialog(f"Error showing search modal: {str(ex)}")
    
    def perform_search(self, e):
        """Perform the search based on selected type"""
        search_type = self.search_type.value
        search_term = self.search_input.value
        
        if not search_term:
            return
            
        # Close modal first
        self.close_modal()
        
        # Perform search based on type
        if search_type == "block_number" or search_type == "block_hash":
            # Use existing block search
            self.gui.block_search_field.value = search_term
            self.gui.search_block(None)
        elif search_type == "transaction_hash":
            self.gui.add_log(f"Searching for transaction: {search_term}")
            # TODO: Implement transaction search
        elif search_type == "address":
            self.gui.add_log(f"Searching for address: {search_term}")
            # TODO: Implement address search
    
    def close_modal(self):
        """Close the modal"""
        if hasattr(self, 'modal'):
            self.modal.open = False
            self.page.update()
    
    def show_error_dialog(self, message):
        """Show error dialog"""
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Error"),
            content=ft.Text(message),
            actions=[ft.TextButton("OK", on_click=lambda e: self.close_error_dialog(dialog))]
        )
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()
    
    def close_error_dialog(self, dialog):
        """Close error dialog"""
        dialog.open = False
        self.page.update()
