#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Qbitcoin Node GUI Application
A comprehensive desktop GUI for managing and monitoring a Qbitcoin blockchain node
using the Flet framework with full wallet integration, P2P settings, API management,
and real-time blockchain monitoring.
"""

import sys
import os
import json
import threading
import time
import datetime
import logging
import subprocess
from typing import Dict
import grpc

# Add qbitcoin path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

import flet as ft
from qbitcoin.core import config
from qbitcoin.tools.wallet_creator import WalletCreator
from qbitcoin.generated import qbit_pb2, qbit_pb2_grpc, qbitwallet_pb2, qbitwallet_pb2_grpc, qbitmining_pb2_grpc
from qbitcoin.core.misc import logger
from pyqrllib.pyqrllib import bin2hstr, hstr2bin

# Import modal dialog components
from modals import BlockDetailsModal, TransactionDetailsModal, WalletDetailsModal


class GUILogHandler(logging.Handler):
    """Custom log handler to capture logs and send them to GUI"""
    
    def __init__(self, gui_instance):
        super().__init__()
        self.gui_instance = gui_instance
        
    def emit(self, record):
        try:
            msg = self.format(record)
            level = record.levelname
            if self.gui_instance:
                self.gui_instance.add_log(msg, level)
        except Exception:
            self.handleError(record)


class QbitcoinGUI:
    """Main GUI Application for Qbitcoin Node Management"""
    
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "Qbitcoin Node Manager"
        self.page.window_width = 1400
        self.page.window_height = 900
        self.page.theme_mode = ft.ThemeMode.DARK  # Force dark theme
        
        # Node and services
        self.node_running = False
        self.wallet_daemon = None
        self.node_process = None  # For the main node process
        
        # gRPC stubs for API communication
        self.public_stub = None
        self.wallet_stub = None
        self.mining_stub = None
        
        # UI State
        self.blockchain_data = []
        self.peer_data = []
        self.transaction_pool = []
        self.debug_logs = []
        
        # Settings
        self.settings = self.load_settings()
        
        # Initialize modal dialogs
        self.block_details_modal = None
        self.transaction_details_modal = None
        self.wallet_details_modal = None
        
        # Initialize log viewer first so logs can be added during setup
        self.log_viewer = ft.ListView(
            height=400,
            spacing=2,
            auto_scroll=True,
            controls=[]
        )
        
        # Setup logging to capture node logs
        self.setup_logging()
        
        # Initialize UI
        self.setup_page()
        self.create_main_layout()
        
        # Initialize modal dialogs
        self.initialize_modals()
        
        # Start background monitoring
        self.start_monitoring()
    
    def load_settings(self) -> Dict:
        """Load application settings"""
        default_settings = {
            "mining_enabled": False,
            "mining_threads": 1,
            "mining_address": "",
            "p2p_port": 19000,
            "api_enabled": True,
            "api_port": 19009,
            "wallet_path": os.path.join(config.user.wallet_dir, "qbitcoin_wallet.json"),
            "node_data_dir": config.user.qrl_dir,
            "log_level": "INFO",
            "auto_start": False
        }
        
        settings_file = os.path.join(config.user.qrl_dir, "gui_settings.json")
        try:
            if os.path.exists(settings_file):
                with open(settings_file, 'r') as f:
                    loaded_settings = json.load(f)
                default_settings.update(loaded_settings)
        except Exception as e:
            print(f"Error loading settings: {e}")
        
        return default_settings
    
    def save_settings(self):
        """Save application settings"""
        settings_file = os.path.join(config.user.qrl_dir, "gui_settings.json")
        try:
            os.makedirs(os.path.dirname(settings_file), exist_ok=True)
            with open(settings_file, 'w') as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            print(f"Error saving settings: {e}")
    
    def connect_grpc_services(self):
        """Connect to gRPC services"""
        try:
            # Connect to public API
            public_channel = grpc.insecure_channel(f'{config.user.public_api_host}:{config.user.public_api_port}')
            self.public_stub = qbit_pb2_grpc.PublicAPIStub(public_channel)
            
            # Connect to wallet API (if wallet daemon is running)
            if self.wallet_daemon:
                wallet_channel = grpc.insecure_channel(f'{config.user.wallet_api_host}:{config.user.wallet_api_port}')
                self.wallet_stub = qbitwallet_pb2_grpc.WalletAPIStub(wallet_channel)
            
            # Connect to mining API
            mining_channel = grpc.insecure_channel(f'{config.user.mining_api_host}:{config.user.mining_api_port}')
            self.mining_stub = qbitmining_pb2_grpc.MiningAPIStub(mining_channel)
            
            self.add_log("Connected to gRPC services")
            return True
            
        except Exception as e:
            self.add_log(f"Error connecting to gRPC services: {e}", "ERROR")
            return False
    
    def get_node_status(self):
        """Get node status from API"""
        try:
            if self.public_stub:
                request = qbit_pb2.GetNodeStateReq()
                response = self.public_stub.GetNodeState(request, timeout=5)
                return response.info
            return None
        except Exception as e:
            self.add_log(f"Error getting node status: {e}", "ERROR")
            return None
    
    def get_wallet_info(self):
        """Get wallet information"""
        try:
            if self.wallet_stub:
                request = qbitwallet_pb2.GetWalletInfoReq()
                response = self.wallet_stub.GetWalletInfo(request, timeout=5)
                return response
            return None
        except Exception as e:
            self.add_log(f"Error getting wallet info: {e}", "ERROR")
            return None
    
    def get_addresses_list(self):
        """Get list of wallet addresses"""
        try:
            if self.wallet_stub:
                request = qbitwallet_pb2.ListAddressesReq()
                response = self.wallet_stub.ListAddresses(request, timeout=5)
                return response.addresses
            return []
        except Exception as e:
            self.add_log(f"Error getting addresses: {e}", "ERROR")
            return []
    
    def get_balance(self, address: str):
        """Get balance for an address"""
        try:
            if self.wallet_stub:
                request = qbitwallet_pb2.BalanceReq(address=address)
                response = self.wallet_stub.GetBalance(request, timeout=5)
                return response.balance
            return "0"
        except Exception as e:
            self.add_log(f"Error getting balance: {e}", "ERROR")
            return "0"
    
    def setup_page(self):
        """Setup page configuration"""
        self.page.bgcolor = ft.Colors.GREY_900  # Dark background
        self.page.scroll = ft.ScrollMode.AUTO
        
        # Status bar
        self.status_text = ft.Text("Ready", size=12, color=ft.Colors.GREEN)
        self.status_bar = ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.CIRCLE, color=ft.Colors.RED, size=12),
                self.status_text,
                ft.Text(f"Qbitcoin Node GUI v{config.dev.version}", size=10, color=ft.Colors.GREY_400)
            ]),
            padding=5,
            bgcolor=ft.Colors.GREY_800,  # Dark status bar
            height=30
        )
    
    def create_main_layout(self):
        """Create the main application layout"""
        # Main tabs
        self.tabs = ft.Tabs(
            selected_index=0,
            animation_duration=300,
            tabs=[
                ft.Tab(text="Dashboard", icon=ft.Icons.DASHBOARD, content=self.create_dashboard_tab()),
                ft.Tab(text="Wallet", icon=ft.Icons.ACCOUNT_BALANCE_WALLET, content=self.create_wallet_tab()),
                ft.Tab(text="Blockchain", icon=ft.Icons.LINK, content=self.create_blockchain_tab()),
                ft.Tab(text="Network", icon=ft.Icons.NETWORK_CHECK, content=self.create_network_tab()),
                ft.Tab(text="Mining", icon=ft.Icons.MEMORY, content=self.create_mining_tab()),
                ft.Tab(text="Settings", icon=ft.Icons.SETTINGS, content=self.create_settings_tab()),
                ft.Tab(text="Debug", icon=ft.Icons.BUG_REPORT, content=self.create_debug_tab()),
            ],
            expand=True
        )
        
        # Main container
        main_container = ft.Column([
            self.create_header(),
            self.tabs,
            self.status_bar
        ], expand=True, spacing=0)
        
        self.page.add(main_container)
    
    def create_header(self):
        """Create application header"""
        return ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.CURRENCY_BITCOIN, size=40, color=ft.Colors.ORANGE),
                ft.Column([
                    ft.Text("Qbitcoin Node Manager", size=24, weight=ft.FontWeight.BOLD),
                    ft.Text("Post-Quantum Blockchain Node", size=12, color=ft.Colors.GREY)
                ], spacing=0),
                ft.Container(expand=True),
                self.create_node_controls()
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            padding=20,
            bgcolor=ft.Colors.BLUE_GREY_900,
            margin=0
        )
    
    def create_node_controls(self):
        """Create node control buttons"""
        self.start_button = ft.ElevatedButton(
            "Start Node",
            icon=ft.Icons.PLAY_ARROW,
            color=ft.Colors.WHITE,
            bgcolor=ft.Colors.GREEN,
            on_click=self.start_node
        )
        
        self.stop_button = ft.ElevatedButton(
            "Stop Node",
            icon=ft.Icons.STOP,
            color=ft.Colors.WHITE,
            bgcolor=ft.Colors.RED,
            on_click=self.stop_node,
            disabled=True
        )
        
        return ft.Row([self.start_button, self.stop_button], spacing=10)
    
    def create_dashboard_tab(self):
        """Create dashboard tab content"""
        # Node status cards
        self.node_status_card = self.create_status_card("Node Status", "Stopped", ft.Colors.RED)
        self.wallet_status_card = self.create_status_card("Wallet Status", "Locked", ft.Colors.ORANGE)
        self.blockchain_status_card = self.create_status_card("Blockchain Height", "0", ft.Colors.BLUE)
        self.network_status_card = self.create_status_card("Connected Peers", "0", ft.Colors.PURPLE)
        
        # Quick stats
        self.balance_card = self.create_info_card("Total Balance", "0.000000000 QBIT")
        self.hashrate_card = self.create_info_card("Mining Hashrate", "0 H/s")
        self.last_block_card = self.create_info_card("Last Block Time", "N/A")
        self.difficulty_card = self.create_info_card("Network Difficulty", "N/A")
        
        # Recent activity
        self.activity_list = ft.ListView(
            height=200,
            spacing=5,
            auto_scroll=True
        )
        
        return ft.Container(
            content=ft.Column([
                ft.Text("Dashboard", size=20, weight=ft.FontWeight.BOLD),
                ft.Row([
                    self.node_status_card,
                    self.wallet_status_card,
                    self.blockchain_status_card,
                    self.network_status_card
                ], spacing=10),
                ft.Row([
                    self.balance_card,
                    self.hashrate_card,
                    self.last_block_card,
                    self.difficulty_card
                ], spacing=10),
                ft.Container(
                    content=ft.Column([
                        ft.Text("Recent Activity", size=16, weight=ft.FontWeight.BOLD),
                        self.activity_list
                    ]),
                    bgcolor=ft.Colors.GREY_800,  # Dark container
                    padding=15,
                    border_radius=10,
                    expand=True
                )
            ], spacing=15),
            padding=20,
            expand=True
        )
    
    def create_wallet_tab(self):
        """Create wallet tab content"""
        # Wallet controls
        self.wallet_unlock_btn = ft.ElevatedButton(
            "Unlock Wallet",
            icon=ft.Icons.LOCK_OPEN,
            on_click=self.unlock_wallet_dialog
        )
        
        self.wallet_create_btn = ft.ElevatedButton(
            "Create Wallet",
            icon=ft.Icons.ADD,
            on_click=self.create_wallet_dialog
        )
        
        self.wallet_backup_btn = ft.ElevatedButton(
            "Backup Wallet",
            icon=ft.Icons.BACKUP,
            on_click=self.backup_wallet_dialog
        )
        
        # Address list
        self.address_list = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Address")),
                ft.DataColumn(ft.Text("Balance")),
                ft.DataColumn(ft.Text("Type")),
                ft.DataColumn(ft.Text("Actions"))
            ],
            rows=[]
        )
        
        # Refresh button for wallet addresses
        self.refresh_wallet_btn = ft.IconButton(
            icon=ft.Icons.REFRESH,
            tooltip="Refresh wallet addresses",
            on_click=self.load_wallet_addresses
        )
        
        # Transaction form
        self.send_to_field = ft.TextField(
            label="Send to Address",
            width=400,
            prefix_icon=ft.Icons.ACCOUNT_BALANCE_WALLET
        )
        
        self.send_amount_field = ft.TextField(
            label="Amount (QBIT)",
            width=200,
            prefix_icon=ft.Icons.MONEY
        )
        
        self.send_fee_field = ft.TextField(
            label="Fee",
            width=150,
            value="0.01",
            prefix_icon=ft.Icons.PAID
        )
        
        self.send_button = ft.ElevatedButton(
            "Send Transaction",
            icon=ft.Icons.SEND,
            on_click=self.send_transaction
        )
        
        # Load wallet addresses when the tab is created
        self.load_wallet()
        
        return ft.Container(
            content=ft.Column([
                ft.Text("Wallet Management", size=20, weight=ft.FontWeight.BOLD),
                
                # Wallet status card
                ft.Container(
                    content=ft.Row([
                        self.create_status_card("Wallet Status", "Not Loaded", ft.Colors.ORANGE),
                        self.create_status_card("Total Balance", "0.0 QBIT", ft.Colors.BLUE),
                        self.refresh_wallet_btn
                    ]),
                    padding=5
                ),
                
                # Wallet controls
                ft.Container(
                    content=ft.Column([
                        ft.Text("Wallet Controls", size=16, weight=ft.FontWeight.BOLD),
                        ft.Row([
                            self.wallet_unlock_btn,
                            self.wallet_create_btn,
                            self.wallet_backup_btn
                        ], spacing=10)
                    ]),
                    bgcolor=ft.Colors.GREY_800,  # Dark container
                    padding=15,
                    border_radius=10
                ),
                
                # Address list
                ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Text("Addresses", size=16, weight=ft.FontWeight.BOLD),
                            ft.IconButton(
                                icon=ft.Icons.REFRESH, 
                                tooltip="Refresh addresses",
                                on_click=self.load_wallet_addresses
                            )
                        ]),
                        ft.ListView(
                            controls=[self.address_list],
                            height=200
                        )
                    ]),
                    bgcolor=ft.Colors.GREY_800,  # Dark container
                    padding=15,
                    border_radius=10
                ),
                
                # Send transaction
                ft.Container(
                    content=ft.Column([
                        ft.Text("Send Transaction", size=16, weight=ft.FontWeight.BOLD),
                        ft.Row([
                            self.send_to_field,
                            self.send_amount_field,
                            self.send_fee_field,
                            self.send_button
                        ], spacing=10, wrap=True)
                    ]),
                    bgcolor=ft.Colors.GREY_800,  # Dark container
                    padding=15,
                    border_radius=10
                )
            ], spacing=15),
            padding=20,
            expand=True
        )
    
    def create_blockchain_tab(self):
        """Create blockchain tab content"""
        # Block explorer
        self.block_search_field = ft.TextField(
            label="Search by Block Height or Hash",
            width=300,
            prefix_icon=ft.Icons.SEARCH
        )
        
        self.block_search_btn = ft.ElevatedButton(
            "Search",
            icon=ft.Icons.SEARCH,
            on_click=self.search_block
        )
        
        # Block list
        self.block_list = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Height")),
                ft.DataColumn(ft.Text("Hash")),
                ft.DataColumn(ft.Text("Timestamp")),
                ft.DataColumn(ft.Text("Transactions")),
                ft.DataColumn(ft.Text("Size")),
                ft.DataColumn(ft.Text("Actions"))
            ],
            rows=[]
        )
        
        # Transaction pool
        self.mempool_list = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Transaction Hash")),
                ft.DataColumn(ft.Text("From")),
                ft.DataColumn(ft.Text("To")),
                ft.DataColumn(ft.Text("Amount")),
                ft.DataColumn(ft.Text("Fee"))
            ],
            rows=[]
        )
        
        return ft.Container(
            content=ft.Column([
                ft.Text("Blockchain Explorer", size=20, weight=ft.FontWeight.BOLD),
                
                # Search
                ft.Container(
                    content=ft.Column([
                        ft.Text("Block Search", size=16, weight=ft.FontWeight.BOLD),
                        ft.Row([self.block_search_field, self.block_search_btn], spacing=10)
                    ]),
                    bgcolor=ft.Colors.GREY_800,
                    padding=15,
                    border_radius=10
                ),
                
                # Recent blocks
                ft.Container(
                    content=ft.Column([
                        ft.Text("Recent Blocks", size=16, weight=ft.FontWeight.BOLD),
                        ft.ListView(
                            controls=[self.block_list],
                            height=250
                        )
                    ]),
                    bgcolor=ft.Colors.GREY_800,
                    padding=15,
                    border_radius=10
                ),
                
                # Memory pool
                ft.Container(
                    content=ft.Column([
                        ft.Text("Memory Pool (Pending Transactions)", size=16, weight=ft.FontWeight.BOLD),
                        ft.ListView(
                            controls=[self.mempool_list],
                            height=200
                        )
                    ]),
                    bgcolor=ft.Colors.GREY_800,
                    padding=15,
                    border_radius=10
                )
            ], spacing=15, scroll=ft.ScrollMode.AUTO),
            padding=20,
            expand=True
        )
    
    def create_network_tab(self):
        """Create network tab content"""
        # Peer list
        self.peer_list = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("IP Address")),
                ft.DataColumn(ft.Text("Port")),
                ft.DataColumn(ft.Text("Version")),
                ft.DataColumn(ft.Text("Height")),
                ft.DataColumn(ft.Text("Ping")),
                ft.DataColumn(ft.Text("Actions"))
            ],
            rows=[]
        )
        
        # Add peer controls
        self.add_peer_field = ft.TextField(
            label="Peer IP:Port",
            width=200,
            prefix_icon=ft.Icons.COMPUTER
        )
        
        self.add_peer_btn = ft.ElevatedButton(
            "Add Peer",
            icon=ft.Icons.ADD,
            on_click=self.add_peer
        )
        
        # Network stats
        self.network_stats = ft.Column([
            ft.Text("Network Statistics", size=16, weight=ft.FontWeight.BOLD),
            ft.Text("Loading...", size=12)
        ])
        
        return ft.Container(
            content=ft.Column([
                ft.Text("Network Management", size=20, weight=ft.FontWeight.BOLD),
                
                # Network stats
                ft.Container(
                    content=self.network_stats,
                    bgcolor=ft.Colors.GREY_800,
                    padding=15,
                    border_radius=10
                ),
                
                # Add peer
                ft.Container(
                    content=ft.Column([
                        ft.Text("Add Peer", size=16, weight=ft.FontWeight.BOLD),
                        ft.Row([self.add_peer_field, self.add_peer_btn], spacing=10)
                    ]),
                    bgcolor=ft.Colors.GREY_800,
                    padding=15,
                    border_radius=10
                ),
                
                # Peer list
                ft.Container(
                    content=ft.Column([
                        ft.Text("Connected Peers", size=16, weight=ft.FontWeight.BOLD),
                        ft.ListView(
                            controls=[self.peer_list],
                            height=300
                        )
                    ]),
                    bgcolor=ft.Colors.GREY_800,
                    padding=15,
                    border_radius=10
                )
            ], spacing=15, scroll=ft.ScrollMode.AUTO),
            padding=20,
            expand=True
        )
    
    def create_mining_tab(self):
        """Create mining tab content"""
        # Mining controls
        self.mining_address_field = ft.TextField(
            label="Mining Address",
            width=400,
            value=self.settings.get("mining_address", ""),
            prefix_icon=ft.Icons.ACCOUNT_BALANCE_WALLET
        )
        
        self.mining_threads_field = ft.TextField(
            label="Threads",
            width=100,
            value=str(self.settings.get("mining_threads", 1)),
            prefix_icon=ft.Icons.MEMORY
        )
        
        self.start_mining_btn = ft.ElevatedButton(
            "Start Mining",
            icon=ft.Icons.PLAY_ARROW,
            color=ft.Colors.WHITE,
            bgcolor=ft.Colors.GREEN,
            on_click=self.start_mining
        )
        
        self.stop_mining_btn = ft.ElevatedButton(
            "Stop Mining",
            icon=ft.Icons.STOP,
            color=ft.Colors.WHITE,
            bgcolor=ft.Colors.RED,
            on_click=self.stop_mining,
            disabled=True
        )
        
        # Mining stats
        self.mining_stats = ft.Column([
            ft.Text("Mining Statistics", size=16, weight=ft.FontWeight.BOLD),
            ft.Text("Not mining", size=12)
        ])
        
        return ft.Container(
            content=ft.Column([
                ft.Text("Mining Configuration", size=20, weight=ft.FontWeight.BOLD),
                
                # Mining controls
                ft.Container(
                    content=ft.Column([
                        ft.Text("Mining Settings", size=16, weight=ft.FontWeight.BOLD),
                        ft.Row([
                            self.mining_address_field,
                            self.mining_threads_field
                        ], spacing=10),
                        ft.Row([
                            self.start_mining_btn,
                            self.stop_mining_btn
                        ], spacing=10)
                    ]),
                    bgcolor=ft.Colors.GREY_800,
                    padding=15,
                    border_radius=10
                ),
                
                # Mining stats
                ft.Container(
                    content=self.mining_stats,
                    bgcolor=ft.Colors.GREY_800,
                    padding=15,
                    border_radius=10,
                    expand=True
                )
            ], spacing=15, scroll=ft.ScrollMode.AUTO),
            padding=20,
            expand=True
        )
    
    def create_settings_tab(self):
        """Create settings tab content"""
        # General settings
        self.auto_start_check = ft.Checkbox(
            label="Auto-start node on GUI launch",
            value=self.settings.get("auto_start", False)
        )
        
        self.data_dir_field = ft.TextField(
            label="Data Directory",
            width=400,
            value=self.settings.get("node_data_dir", config.user.qrl_dir)
        )
        
        # API settings
        self.api_enabled_check = ft.Checkbox(
            label="Enable API Server",
            value=self.settings.get("api_enabled", True)
        )
        
        self.api_port_field = ft.TextField(
            label="API Port",
            width=100,
            value=str(self.settings.get("api_port", 19009))
        )
        
        # P2P settings
        self.p2p_port_field = ft.TextField(
            label="P2P Port",
            width=100,
            value=str(self.settings.get("p2p_port", 19000))
        )
        
        # Log level
        self.log_level_dropdown = ft.Dropdown(
            label="Log Level",
            width=150,
            value=self.settings.get("log_level", "INFO"),
            options=[
                ft.dropdown.Option("DEBUG"),
                ft.dropdown.Option("INFO"),
                ft.dropdown.Option("WARNING"),
                ft.dropdown.Option("ERROR"),
                ft.dropdown.Option("CRITICAL")
            ]
        )
        
        self.save_settings_btn = ft.ElevatedButton(
            "Save Settings",
            icon=ft.Icons.SAVE,
            on_click=self.save_settings_action
        )
        
        return ft.Container(
            content=ft.Column([
                ft.Text("Application Settings", size=20, weight=ft.FontWeight.BOLD),
                
                # General settings
                ft.Container(
                    content=ft.Column([
                        ft.Text("General", size=16, weight=ft.FontWeight.BOLD),
                        self.auto_start_check,
                        self.data_dir_field,
                        self.log_level_dropdown
                    ]),
                    bgcolor=ft.Colors.GREY_800,
                    padding=15,
                    border_radius=10
                ),
                
                # Network settings
                ft.Container(
                    content=ft.Column([
                        ft.Text("Network", size=16, weight=ft.FontWeight.BOLD),
                        ft.Row([
                            self.p2p_port_field,
                            self.api_enabled_check,
                            self.api_port_field
                        ], spacing=10)
                    ]),
                    bgcolor=ft.Colors.GREY_800,
                    padding=15,
                    border_radius=10
                ),
                
                # Save button
                ft.Container(
                    content=self.save_settings_btn,
                    alignment=ft.alignment.center
                )
            ], spacing=15, scroll=ft.ScrollMode.AUTO),
            padding=20,
            expand=True
        )
    
    def create_debug_tab(self):
        """Create debug tab content"""
        # Log viewer was already initialized in __init__
        # Just configure the rest of the tab
        
        # Log controls
        self.clear_logs_btn = ft.ElevatedButton(
            "Clear Logs",
            icon=ft.Icons.CLEAR,
            on_click=self.clear_logs
        )
        
        self.export_logs_btn = ft.ElevatedButton(
            "Export Logs",
            icon=ft.Icons.DOWNLOAD,
            on_click=self.export_logs
        )
        
        # Console input
        self.console_input = ft.TextField(
            label="Console Command",
            width=400,
            on_submit=self.execute_console_command
        )
        
        self.execute_btn = ft.ElevatedButton(
            "Execute",
            icon=ft.Icons.PLAY_ARROW,
            on_click=self.execute_console_command
        )
        
        return ft.Container(
            content=ft.Column([
                ft.Text("Debug Console", size=20, weight=ft.FontWeight.BOLD),
                
                # Log controls
                ft.Container(
                    content=ft.Row([
                        self.clear_logs_btn,
                        self.export_logs_btn
                    ], spacing=10),
                    bgcolor=ft.Colors.GREY_800,
                    padding=15,
                    border_radius=10
                ),
                
                # Log viewer
                ft.Container(
                    content=ft.Column([
                        ft.Text("System Logs", size=16, weight=ft.FontWeight.BOLD),
                        ft.Container(
                            content=self.log_viewer,
                            bgcolor=ft.Colors.BLACK,
                            padding=10,
                            border_radius=5
                        )
                    ]),
                    bgcolor=ft.Colors.GREY_800,
                    padding=15,
                    border_radius=10
                ),
                
                # Console
                ft.Container(
                    content=ft.Column([
                        ft.Text("Console", size=16, weight=ft.FontWeight.BOLD),
                        ft.Row([
                            self.console_input,
                            self.execute_btn
                        ], spacing=10)
                    ]),
                    bgcolor=ft.Colors.GREY_800,
                    padding=15,
                    border_radius=10
                )
            ], spacing=15, scroll=ft.ScrollMode.AUTO),
            padding=20,
            expand=True,
        )
    
    def initialize_modals(self):
        """Initialize modal dialog instances"""
        try:
            self.block_details_modal = BlockDetailsModal(self.page)
            self.transaction_details_modal = TransactionDetailsModal(self.page)
            self.wallet_details_modal = WalletDetailsModal(self.page)
            self.add_log("Modal dialogs initialized successfully")
        except Exception as ex:
            self.add_log(f"Error initializing modals: {str(ex)}", "ERROR")
    
    def show_block_details(self, block_info):
        """Show detailed block information in modal"""
        try:
            if not self.block_details_modal:
                self.initialize_modals()
            
            if self.block_details_modal:
                self.block_details_modal.show(block_info)
                self.add_log(f"Showing details for block #{block_info.header.block_number}")
        except Exception as ex:
            self.add_log(f"Error showing block details: {str(ex)}", "ERROR")
    
    def show_transaction_details(self, transaction):
        """Show detailed transaction information in modal"""
        try:
            if not self.transaction_details_modal:
                self.initialize_modals()
            
            if self.transaction_details_modal:
                self.transaction_details_modal.show(transaction)
                self.add_log("Showing transaction details")
        except Exception as ex:
            self.add_log(f"Error showing transaction details: {str(ex)}", "ERROR")
    
    def show_wallet_details(self, wallet_info):
        """Show detailed wallet information in modal"""
        try:
            if not self.wallet_details_modal:
                self.initialize_modals()
            
            if self.wallet_details_modal:
                self.wallet_details_modal.show(wallet_info)
                self.add_log("Showing wallet details")
        except Exception as ex:
            self.add_log(f"Error showing wallet details: {str(ex)}", "ERROR")

    # Helper methods for UI components
    def create_status_card(self, title: str, value: str, color):
        """Create a status card"""
        return ft.Container(
            content=ft.Column([
                ft.Text(title, size=12, color=ft.Colors.GREY),
                ft.Text(value, size=18, weight=ft.FontWeight.BOLD, color=color)
            ], spacing=5, alignment=ft.MainAxisAlignment.CENTER),
            bgcolor=ft.Colors.GREY_800,
            padding=15,
            border_radius=10,
            width=200,
            height=80
        )
    
    def create_info_card(self, title: str, value: str):
        """Create an info card"""
        return ft.Container(
            content=ft.Column([
                ft.Text(title, size=12, color=ft.Colors.GREY),
                ft.Text(value, size=14, weight=ft.FontWeight.BOLD)
            ], spacing=5, alignment=ft.MainAxisAlignment.CENTER),
            bgcolor=ft.Colors.GREY_800,
            padding=15,
            border_radius=10,
            width=200,
            height=80
        )
    
    # Event handlers
    def start_node(self, e):
        """Start the Qbitcoin node using main()"""
        try:
            self.add_log("Starting Qbitcoin node...")
            
            # Update UI state
            self.start_button.disabled = True
            self.stop_button.disabled = False
            self.update_status("Node Starting...", ft.Colors.ORANGE)
            self.page.update()
            
            def startup_thread():
                try:
                    # Set mining address in config if provided
                    if self.settings.get("mining_address"):
                        mining_addr_str = self.settings["mining_address"]
                        self.add_log(f"Using mining address: {mining_addr_str}")
                    
                    # Import and call main() directly - same as start_qbitcoin.py
                    from qbitcoin.main import main
                    
                    self.add_log("Starting Qbitcoin node via main()...")
                    
                    # Start the node in a subprocess to avoid blocking
                    import sys
                    import subprocess
                    
                    # Build command line arguments for main()
                    cmd = [sys.executable, "-c", """
import os
import sys
sys.path.insert(0, os.path.abspath('.'))
os.environ['PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION'] = 'python'
from qbitcoin.main import main
main()
"""]
                    
                    # Start the node process
                    self.node_process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        universal_newlines=True,
                        cwd=os.path.dirname(__file__)
                    )
                    
                    self.add_log("Node process started")
                    
                    # Give it a moment to start
                    time.sleep(3)
                    
                    # Try to connect to gRPC services
                    if self.connect_grpc_services():
                        self.node_running = True
                        self.update_status("Node Running", ft.Colors.GREEN)
                        self.add_log("Qbitcoin node started successfully")
                    else:
                        self.add_log("Node started but gRPC connection failed", "WARNING")
                        self.node_running = True
                        self.update_status("Node Running (API pending)", ft.Colors.ORANGE)
                    
                    self.page.update()
                    
                    # Monitor node process output
                    def monitor_output():
                        if self.node_process:
                            for line in iter(self.node_process.stdout.readline, ''):
                                if line:
                                    # Clean up the log line and add to GUI
                                    cleaned_line = line.strip()
                                    if cleaned_line:
                                        self.add_log(f"Node: {cleaned_line}")
                                if self.node_process.poll() is not None:
                                    break
                    
                    # Start output monitoring in background
                    threading.Thread(target=monitor_output, daemon=True).start()
                    
                except Exception as ex:
                    self.add_log(f"Error starting node: {str(ex)}", "ERROR")
                    import traceback
                    self.add_log(f"Traceback: {traceback.format_exc()}", "ERROR")
                    self.update_status("Start Failed", ft.Colors.RED)
                    self.start_button.disabled = False
                    self.stop_button.disabled = True
                    self.page.update()
            
            threading.Thread(target=startup_thread, daemon=True).start()
            
        except Exception as ex:
            self.add_log(f"Error starting node: {str(ex)}", "ERROR")
            self.update_status("Start Failed", ft.Colors.RED)
            self.start_button.disabled = False
            self.stop_button.disabled = True
            self.page.update()
    
    def stop_node(self, e):
        """Stop the Qbitcoin node"""
        try:
            self.add_log("Stopping Qbitcoin node...")
            
            # Stop node process
            if self.node_process:
                self.add_log("Terminating node process...")
                self.node_process.terminate()
                
                # Wait for process to terminate gracefully
                try:
                    self.node_process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    self.add_log("Force killing node process...")
                    self.node_process.kill()
                    self.node_process.wait()
                
                self.node_process = None
            
            # Reset connection references
            self.public_stub = None
            self.wallet_stub = None
            self.mining_stub = None
            
            # Update UI state
            self.node_running = False
            self.start_button.disabled = False
            self.stop_button.disabled = True
            self.start_mining_btn.disabled = True
            self.stop_mining_btn.disabled = True
            
            self.update_status("Node Stopped", ft.Colors.RED)
            self.add_log("Qbitcoin node stopped successfully")
            self.page.update()
            
        except Exception as ex:
            self.add_log(f"Error stopping node: {str(ex)}", "ERROR")
    
    def start_mining(self, e):
        """Start mining"""
        try:
            mining_address = self.mining_address_field.value
            threads = int(self.mining_threads_field.value)
            
            if not mining_address:
                self.show_error_dialog("Mining address is required")
                return
            
            if not self.node_running:
                self.show_error_dialog("Node must be running to start mining")
                return
            
            # Validate mining address
            try:
                # Convert Q address to bytes for validation
                if not mining_address.startswith('Q'):
                    self.show_error_dialog("Invalid mining address format")
                    return
            except Exception:
                self.show_error_dialog("Invalid mining address")
                return
            
            # Since we're using main() directly, mining would be controlled via the node's API
            # For now, we'll just update the UI to indicate mining is "started"
            # In a real implementation, you'd use the mining API to start/stop mining
            
            # Update UI
            self.start_mining_btn.disabled = True
            self.stop_mining_btn.disabled = False
            
            # Update settings
            self.settings["mining_address"] = mining_address
            self.settings["mining_threads"] = threads
            self.settings["mining_enabled"] = True
            self.save_settings()
            
            self.add_log(f"Mining configured for {threads} threads with address {mining_address}")
            self.add_log("Note: Mining control via API will be implemented in future updates")
            self.page.update()
            
        except Exception as ex:
            self.add_log(f"Error starting mining: {str(ex)}", "ERROR")
    
    def stop_mining(self, e):
        """Stop mining"""
        try:
            # Since we're using main() directly, mining would be controlled via the node's API
            # For now, we'll just update the UI to indicate mining is "stopped"
            
            # Update UI
            self.start_mining_btn.disabled = False
            self.stop_mining_btn.disabled = True
            
            # Update settings
            self.settings["mining_enabled"] = False
            self.save_settings()
            
            self.add_log("Mining stopped")
            self.add_log("Note: Mining control via API will be implemented in future updates")
            self.page.update()
            
        except Exception as ex:
            self.add_log(f"Error stopping mining: {str(ex)}", "ERROR")
    
    def unlock_wallet_dialog(self, e):
        """Show wallet unlock dialog"""
        from qbitcoin.core.Wallet import Wallet, WalletDecryptionError
        
        def unlock_wallet(e):
            password = password_field.value
            if password:
                try:
                    if not self.wallet:
                        self.wallet = Wallet(wallet_path=self.wallet_path)
                        self.wallet_loaded = True
                    
                    # Try to decrypt the wallet with provided password
                    if self.wallet.encrypted:
                        self.wallet.decrypt(password)
                        self.wallet_unlocked = True
                        self.update_wallet_status("Unlocked", ft.Colors.GREEN)
                        self.add_log("Wallet unlocked successfully")
                        
                        # Reload addresses with updated wallet
                        self.load_wallet_addresses()
                    else:
                        self.add_log("Wallet is not encrypted", "INFO")
                        
                    dialog.open = False
                    self.page.update()
                except WalletDecryptionError as ex:
                    self.add_log("Invalid password. Please try again.", "ERROR")
                    error_text.value = "Invalid password. Please try again."
                    self.page.update()
                except Exception as ex:
                    self.add_log(f"Error unlocking wallet: {str(ex)}", "ERROR")
                    error_text.value = f"Error: {str(ex)}"
                    self.page.update()
        
        password_field = ft.TextField(
            label="Password",
            password=True,
            autofocus=True,
            on_submit=lambda e: unlock_wallet(e)
        )
        
        error_text = ft.Text("", color=ft.Colors.RED_500)
        
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Unlock Wallet"),
            content=ft.Column([
                ft.Text("Enter your wallet password:"),
                password_field,
                error_text
            ], height=100, spacing=10),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: setattr(dialog, 'open', False)),
                ft.TextButton("Unlock", on_click=unlock_wallet)
            ]
        )
        
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()
    
    def create_wallet_dialog(self, e):
        """Show create wallet dialog"""
        from qbitcoin.core.Wallet import Wallet, WalletException
        
        def create_wallet(e):
            name = name_field.value
            password = password_field.value
            
            if not name:
                error_text.value = "Wallet name is required"
                error_text.visible = True
                self.page.update()
                return
            
            try:
                # Create new Falcon-512 wallet
                self.wallet = Wallet(wallet_path=self.wallet_path)
                
                # Check if wallet already exists and has addresses
                if len(self.wallet.address_items) > 0:
                    error_text.value = "A wallet already exists. Use it or delete it before creating a new one."
                    error_text.visible = True
                    self.page.update()
                    return
                
                # Add a new Falcon-512 address
                falcon_keypair = self.wallet.add_new_address()
                
                # Encrypt if password provided
                if password:
                    self.wallet.encrypt(password)
                    self.add_log("Wallet encrypted with provided password")
                
                # Save wallet
                self.wallet.save()
                self.wallet_exists = True
                self.wallet_loaded = True
                
                if not password:
                    self.wallet_unlocked = True
                    self.update_wallet_status("Unlocked", ft.Colors.GREEN)
                else:
                    self.update_wallet_status("Locked", ft.Colors.ORANGE)
                
                # Show success message with the new address
                self.add_log(f"Created new wallet with address: {falcon_keypair['address']}")
                dialog.open = False
                self.page.update()
                
                # Load addresses to update the UI
                self.load_wallet_addresses()
            except Exception as ex:
                self.add_log(f"Error creating wallet: {str(ex)}", "ERROR")
                error_text.value = f"Error: {str(ex)}"
                error_text.visible = True
                self.page.update()
        
        name_field = ft.TextField(
            label="Wallet Name", 
            autofocus=True,
            hint_text="Enter a name for your wallet",
            width=350
        )
        
        password_field = ft.TextField(
            label="Password (Optional)", 
            password=True,
            hint_text="Leave empty for no encryption",
            width=350
        )
        
        confirm_password = ft.TextField(
            label="Confirm Password", 
            password=True,
            width=350
        )
        
        error_text = ft.Text("", color=ft.Colors.RED_500, visible=False)
        
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Create New Wallet"),
            content=ft.Column([
                ft.Text("This will create a new Falcon-512 post-quantum wallet"),
                name_field,
                password_field,
                confirm_password,
                error_text
            ], height=220, spacing=10),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: setattr(dialog, 'open', False)),
                ft.TextButton("Create", on_click=create_wallet)
            ]
        )
        
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()
    
    def backup_wallet_dialog(self, e):
        """Show backup wallet dialog"""
        self.show_info_dialog("Backup wallet feature will be implemented here")
    
    def send_transaction(self, e):
        """Send a transaction"""
        try:
            to_address = self.send_to_field.value
            amount = self.send_amount_field.value
            fee = self.send_fee_field.value
            
            if not to_address or not amount:
                self.show_error_dialog("To address and amount are required")
                return
            
            # Validate and send transaction
            self.add_log(f"Sending {amount} QBIT to {to_address} with fee {fee}")
            
            # Clear fields
            self.send_to_field.value = ""
            self.send_amount_field.value = ""
            self.page.update()
            
        except Exception as ex:
            self.add_log(f"Error sending transaction: {str(ex)}", "ERROR")
    
    def search_block(self, e):
        """Search for a block"""
        search_term = self.block_search_field.value
        if not search_term:
            return
            
        try:
            self.add_log(f"Searching for block: {search_term}")
            
            if not self.node_running or not self.public_stub:
                self.show_error_dialog("Node must be running and connected to search blocks")
                return
            
            # Clear existing block list
            self.block_list.rows.clear()
            
            # Try to parse as block number first, then as hash
            block_info = None
            found = False
            
            # First try: parse as block number
            try:
                block_number = int(search_term)
                self.add_log(f"Searching for block number: {block_number}")
                request = qbit_pb2.GetBlockByNumberReq(block_number=block_number)
                response = self.public_stub.GetBlockByNumber(request, timeout=10)
                block_info = response.block
                self.add_log(f"Found block #{block_number}")
                found = True
                
            except ValueError:
                # Not a valid integer, try as block hash
                self.add_log("Not a valid block number, trying as hash...")
                
            except grpc.RpcError as grpc_ex:
                self.add_log(f"gRPC error getting block by number: {grpc_ex}", "ERROR")
                # Don't return here, might still be a valid hash
                
            # Second try: parse as block hash (only if not found as number)
            if not found:
                try:
                    # Convert hex string to bytes
                    hash_term = search_term
                    if hash_term.startswith('0x'):
                        hash_term = hash_term[2:]
                    
                    # Validate hex format
                    block_hash = bytes.fromhex(hash_term)
                    self.add_log(f"Searching for block hash: {hash_term}")
                    request = qbit_pb2.GetBlockReq(header_hash=block_hash)
                    response = self.public_stub.GetBlock(request, timeout=10)
                    block_info = response.block
                    self.add_log(f"Found block by hash")
                    found = True
                    
                except ValueError as hex_ex:
                    self.add_log(f"Invalid hex format: {hex_ex}", "ERROR")
                    
                except grpc.RpcError as grpc_ex:
                    self.add_log(f"gRPC error getting block by hash: {grpc_ex}", "ERROR")
                    
            if found and block_info:
                # Display block information
                self.display_block_info(block_info)
                self.add_log("Block information displayed")
            else:
                self.show_error_dialog("Block not found")
                
        except Exception as ex:
            self.add_log(f"Error searching for block: {str(ex)}", "ERROR")
            self.show_error_dialog(f"Error searching for block: {str(ex)}")
             
            
            if block_info and found:
                # Display block information
                self.display_block_info(block_info)
                self.add_log("Block information displayed")
            else:
                self.show_error_dialog("Block not found or invalid search term")
                self.add_log("Block not found", "WARNING")
                
        except Exception as ex:
            self.add_log(f"Error searching for block: {str(ex)}", "ERROR")
            self.show_error_dialog(f"Error searching for block: {str(ex)}")
    
    def display_block_info(self, block_info):
        """Display block information in the block list"""
        try:
            # Extract block data
            block_number = block_info.header.block_number
            block_hash = bin2hstr(block_info.header.hash_header)
            timestamp = block_info.header.timestamp_seconds
            tx_count = len(block_info.transactions)
            block_size = len(block_info.SerializeToString())
            
            # Convert timestamp to readable format
            readable_time = datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
            
            # Add special indicator for genesis block
            block_display = str(block_number)
            if block_number == 0:
                block_display = "0 (Genesis)"
            
            # Create "View Details" button
            view_button = ft.ElevatedButton(
                "View Details",
                on_click=lambda e: self.show_block_details(block_info),
                style=ft.ButtonStyle(
                    bgcolor=ft.Colors.BLUE_600,
                    color=ft.Colors.WHITE,
                    padding=ft.Padding(8, 4, 8, 4)
                ),
                height=30
            )
            
            # Add to block list
            self.block_list.rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(block_display)),
                        ft.DataCell(ft.Text(f"{block_hash[:16]}..." if len(block_hash) > 16 else block_hash)),
                        ft.DataCell(ft.Text(readable_time)),
                        ft.DataCell(ft.Text(str(tx_count))),
                        ft.DataCell(ft.Text(f"{block_size:,} bytes")),
                        ft.DataCell(view_button)
                    ]
                )
            )
            
            # Also show detailed block information in logs
            if block_number == 0:
                self.add_log("=" * 50)
                self.add_log("GENESIS BLOCK FOUND!")
                self.add_log("=" * 50)
            
            self.add_log(f"Block #{block_number} Details:")
            self.add_log(f"  Hash: {block_hash}")
            self.add_log(f"  Timestamp: {readable_time}")
            self.add_log(f"  Transactions: {tx_count}")
            self.add_log(f"  Size: {block_size:,} bytes")
            
            if block_number == 0:
                self.add_log("  ** This is the Genesis Block **")
                # Show additional genesis block details
                self.add_log(f"  Previous Hash: {bin2hstr(block_info.header.hash_header_prev) if block_info.header.hash_header_prev else 'None (Genesis)'}")
                self.add_log(f"  Merkle Root: {bin2hstr(block_info.header.merkle_root) if block_info.header.merkle_root else 'N/A'}")
                
                # Show transaction details for genesis block
                if tx_count > 0:
                    self.add_log("  Genesis Block Transactions:")
                    for i, tx in enumerate(block_info.transactions):
                        tx_hash = bin2hstr(tx.transaction_hash) if tx.transaction_hash else "N/A"
                        self.add_log(f"    TX {i}: {tx_hash[:32]}...")
                        
                        # Show more details for first transaction
                        if i == 0:
                            tx_type = getattr(tx, 'type', 'unknown')
                            self.add_log(f"      Type: {tx_type}")
                            
            self.page.update()
            
        except Exception as ex:
            self.add_log(f"Error displaying block info: {str(ex)}", "ERROR")
            
            # Show transaction details for genesis block
            if block_number == 0 and tx_count > 0:
                self.add_log("  Genesis Block Transactions:")
                for i, tx in enumerate(block_info.transactions):
                    tx_hash = bin2hstr(tx.transaction_hash) if tx.transaction_hash else "N/A"
                    self.add_log(f"    TX {i}: {tx_hash[:16]}...")
            
            self.page.update()
            
        except Exception as ex:
            self.add_log(f"Error displaying block info: {str(ex)}", "ERROR")
    
    def add_peer(self, e):
        """Add a new peer"""
        peer_address = self.add_peer_field.value
        if peer_address:
            self.add_log(f"Adding peer: {peer_address}")
            self.add_peer_field.value = ""
            self.page.update()
    
    def save_settings_action(self, e):
        """Save application settings"""
        try:
            self.settings.update({
                "auto_start": self.auto_start_check.value,
                "node_data_dir": self.data_dir_field.value,
                "api_enabled": self.api_enabled_check.value,
                "api_port": int(self.api_port_field.value),
                "p2p_port": int(self.p2p_port_field.value),
                "log_level": self.log_level_dropdown.value,
                "mining_address": self.mining_address_field.value,
                "mining_threads": int(self.mining_threads_field.value)
            })
            
            self.save_settings()
            self.add_log("Settings saved successfully")
            
        except Exception as ex:
            self.add_log(f"Error saving settings: {str(ex)}", "ERROR")
    
    def clear_logs(self, e):
        """Clear debug logs"""
        self.log_viewer.controls.clear()
        self.debug_logs.clear()
        self.page.update()
    
    def export_logs(self, e):
        """Export logs to file"""
        try:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = f"qbitcoin_logs_{timestamp}.txt"
            
            with open(log_file, 'w') as f:
                for log_entry in self.debug_logs:
                    f.write(f"{log_entry}\n")
            
            self.add_log(f"Logs exported to {log_file}")
            
        except Exception as ex:
            self.add_log(f"Error exporting logs: {str(ex)}", "ERROR")
    
    def execute_console_command(self, e):
        """Execute console command"""
        command = self.console_input.value
        if command:
            self.add_log(f"> {command}")
            # Process command here
            self.add_log("Command executed (feature in development)")
            self.console_input.value = ""
            self.page.update()
    
    # Utility methods
    def update_status(self, text: str, color):
        """Update status bar"""
        self.status_text.value = text
        self.status_text.color = color
    
    def add_log(self, message: str, level: str = "INFO"):
        """Add log entry"""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {level}: {message}"
        
        self.debug_logs.append(log_entry)
        
        # Color code by level
        color = ft.Colors.WHITE
        if level == "ERROR":
            color = ft.Colors.RED
        elif level == "WARNING":
            color = ft.Colors.ORANGE
        elif level == "DEBUG":
            color = ft.Colors.GREY
        
        log_control = ft.Text(
            log_entry,
            size=10,
            color=color,
            font_family="monospace"
        )
        
        self.log_viewer.controls.append(log_control)
        
        # Keep only last 1000 log entries
        if len(self.log_viewer.controls) > 1000:
            self.log_viewer.controls.pop(0)
            self.debug_logs.pop(0)
        
        if hasattr(self, 'page'):
            self.page.update()
    
    def show_error_dialog(self, message: str):
        """Show error dialog"""
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Error"),
            content=ft.Text(message),
            actions=[ft.TextButton("OK", on_click=lambda e: setattr(dialog, 'open', False))]
        )
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()
    
    def show_info_dialog(self, message: str):
        """Show info dialog"""
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Information"),
            content=ft.Text(message),
            actions=[ft.TextButton("OK", on_click=lambda e: setattr(dialog, 'open', False))]
        )
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()
    
    def start_monitoring(self):
        """Start background monitoring"""
        def monitor():
            while True:
                try:
                    if self.node_running:
                        # Update dashboard data
                        self.update_dashboard_data()
                    time.sleep(5)  # Update every 5 seconds
                except Exception as ex:
                    self.add_log(f"Monitor error: {str(ex)}", "ERROR")
                    time.sleep(10)
        
        threading.Thread(target=monitor, daemon=True).start()
    
    def update_dashboard_data(self):
        """Update dashboard with real-time data"""
        try:
            if not self.node_running or not self.public_stub:
                return
                
            # Load recent blocks into blockchain tab
            self.load_recent_blocks()
            
            # Update node status
            node_status = self.get_node_status()
            if node_status:
                # Update status display if needed
                pass
                
        except Exception as ex:
            self.add_log(f"Error updating dashboard: {str(ex)}", "ERROR")
    
    def setup_logging(self):
        """Setup logging to capture node logs in GUI"""
        try:
            # Create custom handler for GUI
            self.gui_log_handler = GUILogHandler(self)
            self.gui_log_handler.setLevel(logging.INFO)
            
            # Create formatter
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            self.gui_log_handler.setFormatter(formatter)
            
            # Add handler to QRL logger
            qrl_logger = logging.getLogger('qbitcoin')
            qrl_logger.addHandler(self.gui_log_handler)
            qrl_logger.setLevel(logging.INFO)
            
            # Also add to root logger to catch all logs
            root_logger = logging.getLogger()
            root_logger.addHandler(self.gui_log_handler)
            
            # Add to specific loggers that might be used
            for logger_name in ['qbitcoin.core', 'qbitcoin.services', 'qbitcoin.p2p']:
                specific_logger = logging.getLogger(logger_name)
                specific_logger.addHandler(self.gui_log_handler)
                specific_logger.setLevel(logging.INFO)
            
            self.add_log("Logging system initialized", "INFO")
            
        except Exception as e:
            print(f"Error setting up logging: {e}")
    
    def load_recent_blocks(self):
        """Load recent blocks into the blockchain tab"""
        try:
            if not self.node_running or not self.public_stub:
                return
            
            # Get current blockchain height
            node_state_request = qbit_pb2.GetNodeStateReq()
            node_state_response = self.public_stub.GetNodeState(node_state_request, timeout=5)
            current_height = node_state_response.info.block_height
            
            # Clear existing rows
            self.block_list.rows.clear()
            
            # Always try to load genesis block first (block 0)
            blocks_to_load = []
            
            # Add genesis block
            blocks_to_load.append(0)
            
            # Add recent blocks (last 9 blocks)
            if current_height > 0:
                start_block = max(1, current_height - 8)  # Skip genesis since we already added it
                for block_num in range(current_height, start_block - 1, -1):
                    if block_num not in blocks_to_load:
                        blocks_to_load.append(block_num)
            
            # Load all blocks
            for block_num in blocks_to_load:
                try:
                    request = qbit_pb2.GetBlockByNumberReq(block_number=block_num)
                    response = self.public_stub.GetBlockByNumber(request, timeout=5)
                    block_info = response.block
                    
                    if block_info:
                        # Extract block data
                        block_number = block_info.header.block_number
                        block_hash = bin2hstr(block_info.header.hash_header)
                        timestamp = block_info.header.timestamp_seconds
                        tx_count = len(block_info.transactions)
                        block_size = len(block_info.SerializeToString())
                        
                        # Convert timestamp to readable format
                        readable_time = datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
                        
                        # Add special indicator for genesis block
                        block_display = str(block_number)
                        if block_number == 0:
                            block_display = "0 (Genesis)"
                        
                        # Create view details button
                        view_details_btn = ft.ElevatedButton(
                            "View Details",
                            icon=ft.Icons.VISIBILITY,
                            style=ft.ButtonStyle(
                                color=ft.Colors.WHITE,
                                bgcolor=ft.Colors.BLUE,
                                padding=ft.padding.symmetric(horizontal=8, vertical=4)
                            ),
                            on_click=lambda e, block=block_info: self.show_block_details(block)
                        )
                        
                        # Add to block list
                        self.block_list.rows.append(
                            ft.DataRow(
                                cells=[
                                    ft.DataCell(ft.Text(block_display)),
                                    ft.DataCell(ft.Text(f"{block_hash[:16]}..." if len(block_hash) > 16 else block_hash)),
                                    ft.DataCell(ft.Text(readable_time)),
                                    ft.DataCell(ft.Text(str(tx_count))),
                                    ft.DataCell(ft.Text(f"{block_size:,} bytes")),
                                    ft.DataCell(view_details_btn)
                                ]
                            )
                        )
                        
                         
                except Exception as block_ex:
                    self.add_log(f"Error loading block {block_num}: {block_ex}", "WARNING")
                    continue
            
            # Update the page
            if hasattr(self, 'page'):
                self.page.update()
                
        except Exception as ex:
            self.add_log(f"Error loading recent blocks: {str(ex)}", "ERROR")
    
    def load_wallet(self):
        """Initialize or load wallet"""
        try:
            import os
            from qbitcoin.core.Wallet import Wallet
            
            # Define wallet path based on config
            self.wallet_path = os.path.join(config.user.wallet_dir, config.dev.wallet_dat_filename)
            self.wallet_exists = os.path.exists(self.wallet_path)
            self.wallet_loaded = False
            self.wallet_unlocked = False
            
            # Initialize wallet object (doesn't load yet)
            self.wallet = None
            
            # Show status
            if self.wallet_exists:
                self.add_log(f"Found wallet at: {self.wallet_path}")
                self.update_wallet_status("Found (Locked)", ft.Colors.ORANGE)
            else:
                self.add_log("No wallet found. Create a new wallet to get started.")
                self.update_wallet_status("Not Found", ft.Colors.RED)
                # Automatically show wallet creation dialog
                # Schedule it with a timer to ensure UI is ready first
                self.create_wallet_dialog(None)
                
        except Exception as ex:
            self.add_log(f"Error initializing wallet: {str(ex)}", "ERROR")
            self.update_wallet_status("Error", ft.Colors.RED)
            
    def load_wallet_addresses(self, e=None):
        """Load wallet addresses into UI"""
        try:
            from qbitcoin.core.Wallet import Wallet, WalletException
            import base64
            
            # Clear existing addresses
            self.address_list.rows.clear()
            
            # Check if wallet file exists
            if not self.wallet_exists:
                self.add_log("No wallet file found. Create a wallet first.", "WARNING")
                return
                
            # Initialize wallet if not already
            if not self.wallet:
                self.wallet = Wallet(wallet_path=self.wallet_path)
                self.wallet_loaded = True
                
            # Get all addresses from wallet
            total_balance = 0
            
            for idx, item in enumerate(self.wallet.address_items):
                try:
                    # Get address
                    address = item.qaddress
                    
                    # Get balance (mock for now, would normally come from node API)
                    balance = 0.0
                    try:
                        # If connected to node, try to get actual balance
                        if self.node_running and self.public_stub:
                            # Convert Q address to bytes
                            if address.startswith('Q'):
                                addr_bytes = bytes(hstr2bin(address[1:]))
                                request = qbit_pb2.GetBalanceReq(address=addr_bytes)
                                response = self.public_stub.GetBalance(request, timeout=5)
                                balance = response.balance / 10**9  # Convert quark to Qbitcoin
                                total_balance += balance
                    except:
                        # If error, use 0 balance
                        balance = 0.0
                    
                    # Create "View" button
                    view_button = ft.ElevatedButton(
                        "View",
                        style=ft.ButtonStyle(
                            color=ft.Colors.WHITE,
                            bgcolor=ft.Colors.BLUE,
                            padding=ft.padding.symmetric(horizontal=8, vertical=4)
                        ),
                        on_click=lambda e, addr=address: self.show_wallet_details({'address': addr})
                    )
                    
                    # Add to address list
                    self.address_list.rows.append(
                        ft.DataRow(
                            cells=[
                                ft.DataCell(ft.Text(f"{address[:20]}..." if len(address) > 20 else address)),
                                ft.DataCell(ft.Text(f"{balance:.9f} QBIT")),
                                ft.DataCell(ft.Text("Falcon-512")),
                                ft.DataCell(view_button)
                            ]
                        )
                    )
                except Exception as item_ex:
                    self.add_log(f"Error processing address {idx}: {str(item_ex)}", "WARNING")
                    continue
            
            # Update wallet stats
            self.update_wallet_status(
                "Loaded" if not self.wallet.encrypted else "Locked", 
                ft.Colors.GREEN if not self.wallet.encrypted else ft.Colors.ORANGE
            )
            
            # Update total balance
            self.update_total_balance(total_balance)
            
            # Update UI
            self.page.update()
            self.add_log(f"Loaded {len(self.wallet.address_items)} addresses from wallet")
            
        except Exception as ex:
            self.add_log(f"Error loading wallet addresses: {str(ex)}", "ERROR")
            self.update_wallet_status("Error", ft.Colors.RED)
            
    def update_wallet_status(self, status_text, color):
        """Update wallet status display"""
        # Update the wallet status card on dashboard
        self.wallet_status_card.content.controls[1].value = status_text
        self.wallet_status_card.content.controls[1].color = color
        
        # Update the page if it exists
        if hasattr(self, 'page'):
            self.page.update()
            
    def update_total_balance(self, balance):
        """Update total balance display"""
        # Format the balance with proper precision
        formatted_balance = f"{balance:.9f} QBIT"
        
        try:
            # Update the balance card
            self.balance_card.content.controls[1].value = formatted_balance
            
            # Update the page if it exists
            if hasattr(self, 'page'):
                self.page.update()
        except:
            pass

def main():
    """
    Main function to run the QbitcoinGUI application
    Supports both desktop and web browser modes
    """
    # Create config directories if they don't exist
    from qbitcoin.core import config
    import os
    
    os.makedirs(config.user.wallet_dir, exist_ok=True)
    os.makedirs(config.user.qrl_dir, exist_ok=True)
    
    # Run as web application by default
    ft.app(target=QbitcoinGUI, view=ft.AppView.WEB_BROWSER, port=8080, assets_dir="assets")

if __name__ == "__main__":
    main()

