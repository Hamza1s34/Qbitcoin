# Qbitcoin Blockchain Flowchart

## Core Blockchain Flow

```mermaid
%%{init: { 'theme': 'base', 'themeVariables': { 'primaryColor': '#f0f0f0', 'primaryTextColor': '#323232', 'primaryBorderColor': '#7C0000', 'lineColor': '#7C0000', 'secondaryColor': '#006100', 'tertiaryColor': '#0000A0' } } }%%
flowchart TD
    %% Core blockchain initialization
    subgraph blockchain_init [" Blockchain Initialization "]
        style blockchain_init fill:#e6f7ff,stroke:#0066cc,stroke-width:2px
        A([Start]) --> B{Blockchain Exists?}
        style A fill:#d4f1f9,stroke:#0066cc,stroke-width:2px
        style B fill:#ffe6cc,stroke:#ff9933,stroke-width:2px
        
        B -- Yes --> C[Load Blockchain State]
        B -- No --> D[Create Genesis Block]
        style C fill:#e6ffcc,stroke:#339900,stroke-width:2px
        style D fill:#e6ffcc,stroke:#339900,stroke-width:2px
        
        D --> D1[Process Genesis Transactions]
        D1 --> D2[Initialize Account States]
        style D1 fill:#e6ffcc,stroke:#339900,stroke-width:1px
        style D2 fill:#e6ffcc,stroke:#339900,stroke-width:1px
        
        C --> E[Sync Account Database]
        D2 --> E
        style E fill:#e6ffcc,stroke:#339900,stroke-width:2px
        
        E --> F([Blockchain Ready])
        style F fill:#d4f1f9,stroke:#0066cc,stroke-width:2px
    end
    
    %% Block processing
    subgraph block_process [" Block Processing "]
        style block_process fill:#fff2e6,stroke:#ff9933,stroke-width:2px
        F --> G[Add Block]
        style G fill:#ffe6cc,stroke:#ff9933,stroke-width:2px
        
        G --> G1{Block Height Valid?}
        G1 -- No --> I[Reject Block]
        G1 -- Yes --> G2{Previous Hash Valid?}
        style G1 fill:#ffe6cc,stroke:#ff9933,stroke-width:1px
        style G2 fill:#ffe6cc,stroke:#ff9933,stroke-width:1px
        
        G2 -- No --> I
        G2 -- Yes --> G3{Merkle Root Valid?}
        style G3 fill:#ffe6cc,stroke:#ff9933,stroke-width:1px
        
        G3 -- No --> I
        G3 -- Yes --> G4{Proof of Work Valid?}
        style G4 fill:#ffe6cc,stroke:#ff9933,stroke-width:1px
        
        G4 -- No --> I
        G4 -- Yes --> J[Process Block Transactions]
        style I fill:#ffcccc,stroke:#cc0000,stroke-width:2px
        style J fill:#e6ffcc,stroke:#339900,stroke-width:2px
        
        J --> J1[Validate Transaction Signatures]
        J1 --> J2[Update Account Balances]
        J2 --> J3[Remove Transactions from Mempool]
        style J1 fill:#e6ffcc,stroke:#339900,stroke-width:1px
        style J2 fill:#e6ffcc,stroke:#339900,stroke-width:1px
        style J3 fill:#e6ffcc,stroke:#339900,stroke-width:1px
        
        J3 --> K[Update Blockchain State]
        K --> L[Save Blockchain State]
        style K fill:#e6ffcc,stroke:#339900,stroke-width:2px
        style L fill:#e6ffcc,stroke:#339900,stroke-width:2px
        
        L --> L1[Broadcast Block Success]
        style L1 fill:#e6ccff,stroke:#6600cc,stroke-width:1px
        L1 --> F
    end
    
    %% Blockchain queries
    subgraph queries [" Blockchain Queries "]
        style queries fill:#f3e6ff,stroke:#6600cc,stroke-width:2px
        F --> M[Get Account Info]
        F --> N[Get Balance]
        F --> O[Get Transaction History]
        
        style M fill:#e6ccff,stroke:#6600cc,stroke-width:2px
        style N fill:#e6ccff,stroke:#6600cc,stroke-width:2px
        style O fill:#e6ccff,stroke:#6600cc,stroke-width:2px
    end
    
    %% Blockchain maintenance
    subgraph maintenance [" Blockchain Maintenance "]
        style maintenance fill:#ffebf0,stroke:#cc0066,stroke-width:2px
        F --> P[Export Blockchain]
        F --> Q[Import Blockchain]
        F --> R[Validate Chain]
        F --> S[Rebuild Account State]
        F --> T[Calculate Next Difficulty]
        
        style P fill:#ffccdb,stroke:#cc0066,stroke-width:2px
        style Q fill:#ffccdb,stroke:#cc0066,stroke-width:2px
        style R fill:#ffccdb,stroke:#cc0066,stroke-width:2px
        style S fill:#ffccdb,stroke:#cc0066,stroke-width:2px
        style T fill:#ffccdb,stroke:#cc0066,stroke-width:2px
    end
```

## Transaction Processing Flow

```mermaid
%%{init: { 'theme': 'base', 'themeVariables': { 'primaryColor': '#f0f0f0', 'primaryTextColor': '#323232', 'primaryBorderColor': '#7C0000', 'lineColor': '#7C0000', 'secondaryColor': '#006100', 'tertiaryColor': '#0000A0' } } }%%
flowchart TD
    %% Transaction creation and validation
    subgraph tx_creation [" Transaction Creation "]
        style tx_creation fill:#e6f7ff,stroke:#0066cc,stroke-width:2px
        A1([Start Transaction]) --> A2[Create Transaction]
        style A1 fill:#d4f1f9,stroke:#0066cc,stroke-width:2px
        style A2 fill:#d4f1f9,stroke:#0066cc,stroke-width:2px
        
        A2 --> A3{Transaction Type?}
        style A3 fill:#ffe6cc,stroke:#ff9933,stroke-width:2px
        
        A3 -- Standard --> A4[Create Transaction with Inputs/Outputs]
        A3 -- Coinbase --> A5[Create Coinbase Transaction]
        style A4 fill:#d4f1f9,stroke:#0066cc,stroke-width:1px
        style A5 fill:#d4f1f9,stroke:#0066cc,stroke-width:1px
        
        A4 --> A6[Calculate Transaction Hash]
        A5 --> A6
        style A6 fill:#d4f1f9,stroke:#0066cc,stroke-width:2px
        
        A6 --> A7[Sign Transaction with Falcon]
        style A7 fill:#d4f1f9,stroke:#0066cc,stroke-width:2px
        
        A7 --> A8([Transaction Ready])
        style A8 fill:#d4f1f9,stroke:#0066cc,stroke-width:2px
    end
    
    %% Transaction validation
    subgraph tx_validation [" Transaction Validation "]
        style tx_validation fill:#fff2e6,stroke:#ff9933,stroke-width:2px
        A8 --> B1[Validate Transaction]
        style B1 fill:#ffe6cc,stroke:#ff9933,stroke-width:2px
        
        B1 --> B2{Size Valid?}
        style B2 fill:#ffe6cc,stroke:#ff9933,stroke-width:1px
        
        B2 -- No --> B9[Reject Transaction]
        B2 -- Yes --> B3{Timestamp Valid?}
        style B9 fill:#ffcccc,stroke:#cc0000,stroke-width:2px
        style B3 fill:#ffe6cc,stroke:#ff9933,stroke-width:1px
        
        B3 -- No --> B9
        B3 -- Yes --> B4{Signature Valid?}
        style B4 fill:#ffe6cc,stroke:#ff9933,stroke-width:1px
        
        B4 -- No --> B9
        B4 -- Yes --> B5{Inputs Valid?}
        style B5 fill:#ffe6cc,stroke:#ff9933,stroke-width:1px
        
        B5 -- No --> B9
        B5 -- Yes --> B6{Balance Sufficient?}
        style B6 fill:#ffe6cc,stroke:#ff9933,stroke-width:1px
        
        B6 -- No --> B9
        B6 -- Yes --> B7[Add to Mempool]
        style B7 fill:#e6ffcc,stroke:#339900,stroke-width:2px
        
        B7 --> B8([Transaction Accepted])
        style B8 fill:#e6ffcc,stroke:#339900,stroke-width:2px
    end
    
    %% Public Key Retrieval Flow
    subgraph pubkey_retrieval [" Public Key Retrieval "]
        style pubkey_retrieval fill:#e6f7ff,stroke:#0066cc,stroke-width:2px
        B4 -- Needs Key --> PK1[Get Transaction Input References]
        style PK1 fill:#d4f1f9,stroke:#0066cc,stroke-width:1px
        
        PK1 --> PK2[Find Block with Original Transaction]
        style PK2 fill:#d4f1f9,stroke:#0066cc,stroke-width:1px
        
        PK2 --> PK3[Extract Public Key from Block]
        style PK3 fill:#d4f1f9,stroke:#0066cc,stroke-width:1px
        
        PK3 --> PK4[Verify Signature with Retrieved Key]
        style PK4 fill:#d4f1f9,stroke:#0066cc,stroke-width:1px
        
        PK4 --> B4
    end
    
    %% Mempool management
    subgraph mempool_mgmt [" Mempool Management "]
        style mempool_mgmt fill:#e6ffcc,stroke:#339900,stroke-width:2px
        B8 --> C1[Add to Mempool]
        style C1 fill:#e6ffcc,stroke:#339900,stroke-width:2px
        
        C1 --> C2{Mempool Full?}
        style C2 fill:#ffe6cc,stroke:#ff9933,stroke-width:1px
        
        C2 -- Yes --> C3[Evict Low-Fee Transactions]
        C2 -- No --> C4[Update Address Index]
        style C3 fill:#e6ffcc,stroke:#339900,stroke-width:1px
        style C4 fill:#e6ffcc,stroke:#339900,stroke-width:1px
        
        C3 --> C4
        C4 --> C5[Update Tx Metadata]
        style C5 fill:#e6ffcc,stroke:#339900,stroke-width:1px
        
        C5 --> C6[Save Mempool State]
        style C6 fill:#e6ffcc,stroke:#339900,stroke-width:1px
        
        C6 --> C7[Broadcast Transaction]
        style C7 fill:#e6ccff,stroke:#6600cc,stroke-width:2px
        
        C7 --> C8([Ready for Mining])
        style C8 fill:#e6ffcc,stroke:#339900,stroke-width:2px
        
        %% Link to mining
        C8 -.-> PM1
    end
```

## P2P Network Flow

```mermaid
%%{init: { 'theme': 'base', 'themeVariables': { 'primaryColor': '#f0f0f0', 'primaryTextColor': '#323232', 'primaryBorderColor': '#7C0000', 'lineColor': '#7C0000', 'secondaryColor': '#006100', 'tertiaryColor': '#0000A0' } } }%%
flowchart TD
    %% P2P Network Initialization
    subgraph network_init [" P2P Network Initialization "]
        style network_init fill:#e6f7ff,stroke:#0066cc,stroke-width:2px
        P1([Start P2P Network]) --> P2[Initialize Network]
        style P1 fill:#d4f1f9,stroke:#0066cc,stroke-width:2px
        style P2 fill:#d4f1f9,stroke:#0066cc,stroke-width:2px
        
        P2 --> P3[Start Listener]
        P2 --> P4[Bootstrap Connections]
        style P3 fill:#d4f1f9,stroke:#0066cc,stroke-width:1px
        style P4 fill:#d4f1f9,stroke:#0066cc,stroke-width:1px
        
        P4 --> P5[Connect to Seed Nodes]
        style P5 fill:#d4f1f9,stroke:#0066cc,stroke-width:1px
        
        P3 --> P6[Accept Incoming Connections]
        P5 --> P6
        style P6 fill:#d4f1f9,stroke:#0066cc,stroke-width:2px
        
        P6 --> P7[Handshake with Peers]
        style P7 fill:#d4f1f9,stroke:#0066cc,stroke-width:2px
        
        P7 --> P8([Network Ready])
        style P8 fill:#d4f1f9,stroke:#0066cc,stroke-width:2px
    end
    
    %% Peer Connection Management
    subgraph peer_mgmt [" Peer Connection Management "]
        style peer_mgmt fill:#fff2e6,stroke:#ff9933,stroke-width:2px
        P8 --> Q1[Maintain Connections]
        style Q1 fill:#ffe6cc,stroke:#ff9933,stroke-width:2px
        
        Q1 --> Q2[Ping Peers]
        Q1 --> Q3[Discover New Peers]
        Q1 --> Q4[Clean Inactive Peers]
        style Q2 fill:#ffe6cc,stroke:#ff9933,stroke-width:1px
        style Q3 fill:#ffe6cc,stroke:#ff9933,stroke-width:1px
        style Q4 fill:#ffe6cc,stroke:#ff9933,stroke-width:1px
        
        Q2 --> Q5{Peer Responsive?}
        style Q5 fill:#ffe6cc,stroke:#ff9933,stroke-width:1px
        
        Q5 -- Yes --> Q6[Update Peer Last Seen]
        Q5 -- No --> Q7[Mark Connection Failure]
        style Q6 fill:#ffe6cc,stroke:#ff9933,stroke-width:1px
        style Q7 fill:#ffe6cc,stroke:#ff9933,stroke-width:1px
        
        Q7 --> Q8{Too Many Failures?}
        style Q8 fill:#ffe6cc,stroke:#ff9933,stroke-width:1px
        
        Q8 -- Yes --> Q9[Ban Peer]
        Q8 -- No --> Q6
        style Q9 fill:#ffcccc,stroke:#cc0000,stroke-width:1px
        
        Q3 --> Q10[Request Peers List]
        style Q10 fill:#ffe6cc,stroke:#ff9933,stroke-width:1px
        
        Q10 --> Q11[Add New Peer Addresses]
        style Q11 fill:#ffe6cc,stroke:#ff9933,stroke-width:1px
        
        Q4 --> Q12[Remove Stale Connections]
        style Q12 fill:#ffe6cc,stroke:#ff9933,stroke-width:1px
        
        Q6 --> Q13([Peers Managed])
        Q9 --> Q13
        Q11 --> Q13
        Q12 --> Q13
        style Q13 fill:#ffe6cc,stroke:#ff9933,stroke-width:2px
    end
    
    %% Message Handling
    subgraph msg_handling [" P2P Message Handling "]
        style msg_handling fill:#e6ccff,stroke:#6600cc,stroke-width:2px
        P8 --> R1[Message Handler]
        style R1 fill:#e6ccff,stroke:#6600cc,stroke-width:2px
        
        R1 --> R2{Message Type?}
        style R2 fill:#e6ccff,stroke:#6600cc,stroke-width:2px
        
        R2 -- Handshake --> R3[Process Handshake]
        R2 -- Ping --> R4[Send Pong]
        R2 -- Transaction --> R5[Process Transaction]
        R2 -- Block --> R6[Process Block]
        R2 -- GetBlocks --> R7[Send Block Inventory]
        R2 -- GetPeers --> R8[Share Peer List]
        style R3 fill:#e6ccff,stroke:#6600cc,stroke-width:1px
        style R4 fill:#e6ccff,stroke:#6600cc,stroke-width:1px
        style R5 fill:#e6ccff,stroke:#6600cc,stroke-width:1px
        style R6 fill:#e6ccff,stroke:#6600cc,stroke-width:1px
        style R7 fill:#e6ccff,stroke:#6600cc,stroke-width:1px
        style R8 fill:#e6ccff,stroke:#6600cc,stroke-width:1px
        
        R3 --> R9([Update Peer Info])
        R4 --> R9
        R5 --> R10([Add to Mempool])
        R6 --> R11([Add to Blockchain])
        R7 --> R9
        R8 --> R9
        style R9 fill:#e6ccff,stroke:#6600cc,stroke-width:1px
        style R10 fill:#e6ccff,stroke:#6600cc,stroke-width:1px
        style R11 fill:#e6ccff,stroke:#6600cc,stroke-width:1px
    end
    
    %% Blockchain Synchronization
    subgraph blockchain_sync [" Blockchain Synchronization "]
        style blockchain_sync fill:#ffebf0,stroke:#cc0066,stroke-width:2px
        P8 --> S1[Start Blockchain Sync]
        style S1 fill:#ffccdb,stroke:#cc0066,stroke-width:2px
        
        S1 --> S2[Get Headers from Peers]
        style S2 fill:#ffccdb,stroke:#cc0066,stroke-width:1px
        
        S2 --> S3{Headers Valid?}
        style S3 fill:#ffccdb,stroke:#cc0066,stroke-width:1px
        
        S3 -- No --> S4[Request from Different Peer]
        S3 -- Yes --> S5[Request Missing Blocks]
        style S4 fill:#ffccdb,stroke:#cc0066,stroke-width:1px
        style S5 fill:#ffccdb,stroke:#cc0066,stroke-width:1px
        
        S4 --> S2
        S5 --> S6[Process Received Blocks]
        style S6 fill:#ffccdb,stroke:#cc0066,stroke-width:1px
        
        S6 --> S7{All Blocks Synced?}
        style S7 fill:#ffccdb,stroke:#cc0066,stroke-width:1px
        
        S7 -- No --> S5
        S7 -- Yes --> S8[Update Blockchain State]
        style S8 fill:#ffccdb,stroke:#cc0066,stroke-width:1px
        
        S8 --> S9([Blockchain Synchronized])
        style S9 fill:#ffccdb,stroke:#cc0066,stroke-width:2px
    end
```

## Data Storage Flow

```mermaid
%%{init: { 'theme': 'base', 'themeVariables': { 'primaryColor': '#f0f0f0', 'primaryTextColor': '#323232', 'primaryBorderColor': '#7C0000', 'lineColor': '#7C0000', 'secondaryColor': '#006100', 'tertiaryColor': '#0000A0' } } }%%
flowchart TD
    %% Chain Manager Storage
    subgraph chain_storage [" Chain Manager Storage "]
        style chain_storage fill:#e6f7ff,stroke:#0066cc,stroke-width:2px
        CM1([Store Block]) --> CM2{File Size Check}
        style CM1 fill:#d4f1f9,stroke:#0066cc,stroke-width:2px
        style CM2 fill:#d4f1f9,stroke:#0066cc,stroke-width:1px
        
        CM2 -- Full --> CM3[Create New Block File]
        CM2 -- Space Available --> CM4[Open Current File]
        style CM3 fill:#d4f1f9,stroke:#0066cc,stroke-width:1px
        style CM4 fill:#d4f1f9,stroke:#0066cc,stroke-width:1px
        
        CM3 --> CM5[Serialize Block]
        CM4 --> CM5
        style CM5 fill:#d4f1f9,stroke:#0066cc,stroke-width:2px
        
        CM5 --> CM6[Write Magic Bytes]
        CM6 --> CM7[Write Block Size]
        CM7 --> CM8[Write Block Data]
        style CM6 fill:#d4f1f9,stroke:#0066cc,stroke-width:1px
        style CM7 fill:#d4f1f9,stroke:#0066cc,stroke-width:1px
        style CM8 fill:#d4f1f9,stroke:#0066cc,stroke-width:1px
        
        CM8 --> CM9[Update Block Index]
        style CM9 fill:#d4f1f9,stroke:#0066cc,stroke-width:2px
        
        CM9 --> CM10[Save Block Index]
        style CM10 fill:#d4f1f9,stroke:#0066cc,stroke-width:2px
    end
    
    %% Account Database
    subgraph account_db [" Account Database "]
        style account_db fill:#fff2e6,stroke:#ff9933,stroke-width:2px
        AD1([Update Account]) --> AD2[Get Account]
        style AD1 fill:#ffe6cc,stroke:#ff9933,stroke-width:2px
        style AD2 fill:#ffe6cc,stroke:#ff9933,stroke-width:1px
        
        AD2 --> AD3{Account Exists?}
        style AD3 fill:#ffe6cc,stroke:#ff9933,stroke-width:1px
        
        AD3 -- Yes --> AD4[Update Balance]
        AD3 -- No --> AD5[Create Account]
        style AD4 fill:#ffe6cc,stroke:#ff9933,stroke-width:1px
        style AD5 fill:#ffe6cc,stroke:#ff9933,stroke-width:1px
        
        AD4 --> AD6[Update Transaction History]
        AD5 --> AD6
        style AD6 fill:#ffe6cc,stroke:#ff9933,stroke-width:1px
        
        AD6 --> AD7[Store Block Reference for Public Key]
        style AD7 fill:#ffe6cc,stroke:#ff9933,stroke-width:1px
        
        AD7 --> AD8[Save Account Data]
        style AD8 fill:#ffe6cc,stroke:#ff9933,stroke-width:2px
    end
    
    %% Mempool Storage
    subgraph mempool_storage [" Mempool Storage "]
        style mempool_storage fill:#e6ffcc,stroke:#339900,stroke-width:2px
        MP1([Save Mempool]) --> MP2[Serialize Transactions]
        style MP1 fill:#e6ffcc,stroke:#339900,stroke-width:2px
        style MP2 fill:#e6ffcc,stroke:#339900,stroke-width:1px
        
        MP2 --> MP3[Create Temp File]
        style MP3 fill:#e6ffcc,stroke:#339900,stroke-width:1px
        
        MP3 --> MP4[Write Transaction Data]
        style MP4 fill:#e6ffcc,stroke:#339900,stroke-width:1px
        
        MP4 --> MP5[Move to Mempool File]
        style MP5 fill:#e6ffcc,stroke:#339900,stroke-width:2px
    end
```

## Cryptocurrency System Components

```mermaid
%%{init: { 'theme': 'base', 'themeVariables': { 'primaryColor': '#f0f0f0', 'primaryTextColor': '#323232', 'primaryBorderColor': '#7C0000', 'lineColor': '#7C0000', 'secondaryColor': '#006100', 'tertiaryColor': '#0000A0' } } }%%
graph TD
    %% Define all nodes first
    Blockchain[Blockchain]
    BlockManager[Block Manager]
    AccountDB[Account Database]
    DifficultyAdjuster[Difficulty Adjuster]
    PoW[Proof of Work]
    
    Transaction[Transaction]
    FalconCrypto[Falcon Cryptography]
    BlockRetriever[Block Retriever]
    
    P2PNetwork[P2P Network]
    MsgHandler[Message Handler]
    PeerManager[Peer Manager]
    Syncer[Blockchain Syncer]
    
    Mempool[Mempool]
    TxValidator[Transaction Validator]
    BlockMiner[Block Miner]
    
    %% Define connections
    Blockchain --> BlockManager
    Blockchain --> AccountDB
    Blockchain --> DifficultyAdjuster
    Blockchain --> PoW
    
    Transaction --> FalconCrypto
    Transaction --> BlockRetriever
    
    P2PNetwork --> MsgHandler
    P2PNetwork --> PeerManager
    P2PNetwork --> Syncer
    
    Mempool --> TxValidator
    BlockMiner --> PoW
    BlockMiner --> Mempool
    
    %% Cross-component connections
    Blockchain --- Mempool
    Blockchain --- P2PNetwork
    Blockchain --- BlockMiner
    
    Transaction --- Blockchain
    Transaction --- Mempool
    
    P2PNetwork --- Mempool
    P2PNetwork --- BlockMiner
    
    BlockRetriever --- Blockchain
    
    %% Now apply styles after all nodes are defined
    style Blockchain fill:#d4f1f9,stroke:#0066cc,stroke-width:3px
    style BlockManager fill:#d4f1f9,stroke:#0066cc,stroke-width:2px
    style AccountDB fill:#ffe6cc,stroke:#ff9933,stroke-width:2px
    style DifficultyAdjuster fill:#ffccdb,stroke:#cc0066,stroke-width:2px
    style PoW fill:#ffccdb,stroke:#cc0066,stroke-width:2px
    
    style Transaction fill:#e6ffcc,stroke:#339900,stroke-width:3px
    style FalconCrypto fill:#e6ccff,stroke:#6600cc,stroke-width:2px
    style BlockRetriever fill:#d4f1f9,stroke:#0066cc,stroke-width:2px
    
    style P2PNetwork fill:#e6ccff,stroke:#6600cc,stroke-width:3px
    style MsgHandler fill:#e6ccff,stroke:#6600cc,stroke-width:2px
    style PeerManager fill:#e6ccff,stroke:#6600cc,stroke-width:2px
    style Syncer fill:#e6ccff,stroke:#6600cc,stroke-width:2px
    
    style Mempool fill:#e6ffcc,stroke:#339900,stroke-width:3px
    style TxValidator fill:#ffe6cc,stroke:#ff9933,stroke-width:2px
    style BlockMiner fill:#ffccdb,stroke:#cc0066,stroke-width:3px
    
    %% Style links
    linkStyle 0 stroke:#0066cc,stroke-width:1px
    linkStyle 1 stroke:#0066cc,stroke-width:1px
    linkStyle 2 stroke:#0066cc,stroke-width:1px
    linkStyle 3 stroke:#0066cc,stroke-width:1px
    linkStyle 4 stroke:#339900,stroke-width:1px
    linkStyle 5 stroke:#339900,stroke-width:1px
    linkStyle 6 stroke:#6600cc,stroke-width:1px
    linkStyle 7 stroke:#6600cc,stroke-width:1px
    linkStyle 8 stroke:#6600cc,stroke-width:1px
    linkStyle 9 stroke:#339900,stroke-width:1px
    linkStyle 10 stroke:#cc0066,stroke-width:1px
    linkStyle 11 stroke:#cc0066,stroke-width:1px
    linkStyle 12 stroke:#0066cc,stroke-width:2px
    linkStyle 13 stroke:#0066cc,stroke-width:2px
    linkStyle 14 stroke:#0066cc,stroke-width:2px
    linkStyle 15 stroke:#339900,stroke-width:2px
    linkStyle 16 stroke:#339900,stroke-width:2px
    linkStyle 17 stroke:#6600cc,stroke-width:2px
    linkStyle 18 stroke:#6600cc,stroke-width:2px
    linkStyle 19 stroke:#0066cc,stroke-width:2px
```

## Mining and Consensus Flow

```mermaid
%%{init: { 'theme': 'base', 'themeVariables': { 'primaryColor': '#f0f0f0', 'primaryTextColor': '#323232', 'primaryBorderColor': '#7C0000', 'lineColor': '#7C0000', 'secondaryColor': '#006100', 'tertiaryColor': '#0000A0' } } }%%
flowchart TD
    %% Mining initialization
    subgraph mining_init [" Mining Initialization "]
        style mining_init fill:#ffebf0,stroke:#cc0066,stroke-width:2px
        PM1([Start Mining]) --> PM2[Set Reward Address]
        style PM1 fill:#ffccdb,stroke:#cc0066,stroke-width:2px
        style PM2 fill:#ffccdb,stroke:#cc0066,stroke-width:2px
        
        PM2 --> PM3[Start Mining Thread]
        style PM3 fill:#ffccdb,stroke:#cc0066,stroke-width:2px
        
        PM3 --> PM4([Mining Thread Running])
        style PM4 fill:#ffccdb,stroke:#cc0066,stroke-width:2px
    end
    
    %% Block creation
    subgraph block_creation [" Block Creation "]
        style block_creation fill:#ffebf0,stroke:#cc0066,stroke-width:2px
        PM4 --> BC1[Get Current Blockchain State]
        style BC1 fill:#ffccdb,stroke:#cc0066,stroke-width:1px
        
        BC1 --> BC2[Get Next Block Difficulty]
        style BC2 fill:#ffccdb,stroke:#cc0066,stroke-width:1px
        
        BC2 --> BC3[Create Coinbase Transaction]
        style BC3 fill:#ffccdb,stroke:#cc0066,stroke-width:1px
        
        BC3 --> BC4[Select Transactions from Mempool]
        style BC4 fill:#ffccdb,stroke:#cc0066,stroke-width:1px
        
        BC4 --> BC5[Calculate Merkle Root]
        style BC5 fill:#ffccdb,stroke:#cc0066,stroke-width:1px
        
        BC5 --> BC6[Prepare Block Header]
        style BC6 fill:#ffccdb,stroke:#cc0066,stroke-width:1px
        
        BC6 --> BC7([Ready for Mining])
        style BC7 fill:#ffccdb,stroke:#cc0066,stroke-width:1px
    end
    
    %% Proof of Work
    subgraph pow_mining [" Proof of Work Mining "]
        style pow_mining fill:#ffebf0,stroke:#cc0066,stroke-width:2px
        BC7 --> POW1[Initialize PoW Solver]
        style POW1 fill:#ffccdb,stroke:#cc0066,stroke-width:1px
        
        POW1 --> POW2[Calculate Target from Difficulty]
        style POW2 fill:#ffccdb,stroke:#cc0066,stroke-width:1px
        
        POW2 --> POW3[Start Mining Loop]
        style POW3 fill:#ffccdb,stroke:#cc0066,stroke-width:1px
        
        POW3 --> POW4[Try Nonce Value]
        style POW4 fill:#ffccdb,stroke:#cc0066,stroke-width:1px
        
        POW4 --> POW5[Compute Block Hash with SHA3-256]
        style POW5 fill:#ffccdb,stroke:#cc0066,stroke-width:1px
        
        POW5 --> POW6{Hash Meets Target?}
        style POW6 fill:#ffccdb,stroke:#cc0066,stroke-width:1px
        
        POW6 -- No --> POW7[Increment Nonce]
        POW6 -- Yes --> POW8[Block Successfully Mined]
        style POW7 fill:#ffccdb,stroke:#cc0066,stroke-width:1px
        style POW8 fill:#ffccdb,stroke:#cc0066,stroke-width:1px
        
        POW7 --> POW4
        POW8 --> POW9[Create Final Block with Transactions]
        style POW9 fill:#ffccdb,stroke:#cc0066,stroke-width:1px
        
        POW9 --> POW10([Block Ready])
        style POW10 fill:#ffccdb,stroke:#cc0066,stroke-width:1px
    end
    
    %% Difficulty Adjustment
    subgraph diff_adjust [" Difficulty Adjustment "]
        style diff_adjust fill:#ffebf0,stroke:#cc0066,stroke-width:2px
        DA1([Calculate Next Difficulty]) --> DA2[Get Block Height]
        style DA1 fill:#ffccdb,stroke:#cc0066,stroke-width:2px
        style DA2 fill:#ffccdb,stroke:#cc0066,stroke-width:1px
        
        DA2 --> DA3{Adjustment Block?}
        style DA3 fill:#ffccdb,stroke:#cc0066,stroke-width:1px
        
        DA3 -- No --> DA4[Return Current Difficulty]
        DA3 -- Yes --> DA5[Get Timespan for Last N Blocks]
        style DA4 fill:#ffccdb,stroke:#cc0066,stroke-width:1px
        style DA5 fill:#ffccdb,stroke:#cc0066,stroke-width:1px
        
        DA5 --> DA6[Calculate Adjustment Ratio]
        style DA6 fill:#ffccdb,stroke:#cc0066,stroke-width:1px
        
        DA6 --> DA7[Apply Adjustment Limits]
        style DA7 fill:#ffccdb,stroke:#cc0066,stroke-width:1px
        
        DA7 --> DA8[Calculate New Difficulty]
        style DA8 fill:#ffccdb,stroke:#cc0066,stroke-width:1px
        
        DA8 --> DA9[Enforce Minimum Difficulty]
        style DA9 fill:#ffccdb,stroke:#cc0066,stroke-width:1px
        
        DA9 --> DA10([Return New Difficulty])
        DA4 --> DA10
        style DA10 fill:#ffccdb,stroke:#cc0066,stroke-width:2px
    end
    
    %% Block submission
    subgraph block_submission [" Block Submission "]
        style block_submission fill:#ffebf0,stroke:#cc0066,stroke-width:2px
        POW10 --> BS1[Add Block to Blockchain]
        style BS1 fill:#ffccdb,stroke:#cc0066,stroke-width:1px
        
        BS1 --> BS2[Broadcast Block to Network]
        style BS2 fill:#ffccdb,stroke:#cc0066,stroke-width:1px
        
        BS2 --> BS3[Update Mining Statistics]
        style BS3 fill:#ffccdb,stroke:#cc0066,stroke-width:1px
        
        BS3 --> BS4([Mining Loop Continues])
        style BS4 fill:#ffccdb,stroke:#cc0066,stroke-width:1px
        
        BS4 -.-> BC1
    end
    
    %% Connect subgraphs
    PM4 --> BC1
    BC7 --> POW1
    DA10 -.-> BC2
    POW10 --> BS1
    
    %% Connect with transaction flow
    C8 -.-> PM1
```
