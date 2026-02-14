-- Dish-Chat Database Migration Script
-- This script fixes all schema issues for portable deployment
-- Run this after creating the initial database and tables

-- ============================================================================
-- STEP 1: Create Missing Enum Types
-- ============================================================================

DO $$
BEGIN
    -- Chat Status Enum
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'chatstatusenum') THEN
        CREATE TYPE chatstatusenum AS ENUM ('normal', 'readonly');
        RAISE NOTICE 'Created chatstatusenum type';
    END IF;
    
    -- Message Role Enum
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'message_role_enum') THEN
        CREATE TYPE message_role_enum AS ENUM ('user', 'assistant', 'tool');
        RAISE NOTICE 'Created message_role_enum type';
    END IF;
END$$;

-- ============================================================================
-- STEP 2: Fix UUID Column Types in CHAT Table
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE 'Fixing UUID columns in chat table...';
    
    -- Drop foreign key constraints temporarily
    ALTER TABLE message DROP CONSTRAINT IF EXISTS message_chat_id_fkey;
    ALTER TABLE chat DROP CONSTRAINT IF EXISTS chat_group_id_fkey;
    
    -- Fix chat table columns (only if they're VARCHAR)
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'chat' AND column_name = 'chat_id' AND data_type = 'character varying'
    ) THEN
        ALTER TABLE chat ALTER COLUMN chat_id TYPE UUID USING chat_id::UUID;
        RAISE NOTICE 'Fixed chat.chat_id to UUID';
    END IF;
    
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'chat' AND column_name = 'active_checkpoint' AND data_type = 'character varying'
    ) THEN
        ALTER TABLE chat ALTER COLUMN active_checkpoint TYPE UUID USING 
            CASE 
                WHEN active_checkpoint IS NULL OR active_checkpoint = '' THEN NULL
                ELSE active_checkpoint::UUID 
            END;
        RAISE NOTICE 'Fixed chat.active_checkpoint to UUID';
    END IF;
    
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'chat' AND column_name = 'group_id' AND data_type = 'character varying'
    ) THEN
        ALTER TABLE chat ALTER COLUMN group_id TYPE UUID USING 
            CASE 
                WHEN group_id IS NULL OR group_id = '' THEN NULL
                ELSE group_id::UUID 
            END;
        RAISE NOTICE 'Fixed chat.group_id to UUID';
    END IF;
    
    -- Fix chat.status column to use enum (if it's VARCHAR)
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'chat' AND column_name = 'status' AND data_type = 'character varying'
    ) THEN
        ALTER TABLE chat ALTER COLUMN status DROP DEFAULT;
        ALTER TABLE chat ALTER COLUMN status TYPE chatstatusenum USING status::chatstatusenum;
        ALTER TABLE chat ALTER COLUMN status SET DEFAULT 'normal'::chatstatusenum;
        RAISE NOTICE 'Fixed chat.status to chatstatusenum';
    END IF;
END$$;

-- ============================================================================
-- STEP 3: Fix UUID Column Types in MESSAGE Table
-- ============================================================================

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'message' AND column_name = 'message_id' AND data_type = 'character varying'
    ) THEN
        ALTER TABLE message ALTER COLUMN message_id TYPE UUID USING message_id::UUID;
        RAISE NOTICE 'Fixed message.message_id to UUID';
    END IF;
    
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'message' AND column_name = 'chat_id' AND data_type = 'character varying'
    ) THEN
        ALTER TABLE message ALTER COLUMN chat_id TYPE UUID USING chat_id::UUID;
        RAISE NOTICE 'Fixed message.chat_id to UUID';
    END IF;
END$$;

-- ============================================================================
-- STEP 4: Fix UUID Column Types in CHAT_GROUP Table
-- ============================================================================

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'chat_group' AND column_name = 'group_id' AND data_type = 'character varying'
    ) THEN
        ALTER TABLE chat_group ALTER COLUMN group_id TYPE UUID USING group_id::UUID;
        RAISE NOTICE 'Fixed chat_group.group_id to UUID';
    END IF;
END$$;

-- ============================================================================
-- STEP 5: Fix UUID Column Types in USER_STATE Table
-- ============================================================================

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'user_state' AND column_name = 'current_chat_id' AND data_type = 'character varying'
    ) THEN
        ALTER TABLE user_state ALTER COLUMN current_chat_id TYPE UUID USING 
            CASE 
                WHEN current_chat_id IS NULL OR current_chat_id = '' THEN NULL
                ELSE current_chat_id::UUID 
            END;
        RAISE NOTICE 'Fixed user_state.current_chat_id to UUID';
    END IF;
END$$;

-- ============================================================================
-- STEP 6: Recreate Foreign Key Constraints
-- ============================================================================

DO $$
BEGIN
    -- Recreate message -> chat foreign key
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'message_chat_id_fkey' AND table_name = 'message'
    ) THEN
        ALTER TABLE message ADD CONSTRAINT message_chat_id_fkey 
            FOREIGN KEY (chat_id) REFERENCES chat(chat_id) ON DELETE CASCADE;
        RAISE NOTICE 'Recreated message_chat_id_fkey';
    END IF;
    
    -- Recreate chat -> chat_group foreign key
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'chat_group_id_fkey' AND table_name = 'chat'
    ) THEN
        ALTER TABLE chat ADD CONSTRAINT chat_group_id_fkey 
            FOREIGN KEY (group_id) REFERENCES chat_group(group_id) ON DELETE SET NULL;
        RAISE NOTICE 'Recreated chat_group_id_fkey';
    END IF;
END$$;

-- ============================================================================
-- STEP 7: Create MESSAGE_METADATA Table
-- ============================================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_name = 'message_metadata'
    ) THEN
        CREATE TABLE message_metadata (
            checkpoint_id TEXT PRIMARY KEY,
            message_id UUID NOT NULL,
            chat_id UUID NOT NULL,
            role message_role_enum NOT NULL,
            message_config JSONB,
            parent_checkpoint_id TEXT,
            FOREIGN KEY (chat_id) REFERENCES chat(chat_id) ON DELETE CASCADE
        );
        
        CREATE INDEX idx_message_chat_id ON message_metadata(chat_id);
        CREATE INDEX idx_message_message_id ON message_metadata(message_id);
        
        RAISE NOTICE 'Created message_metadata table';
    ELSE
        RAISE NOTICE 'message_metadata table already exists';
    END IF;
END$$;

-- ============================================================================
-- VERIFICATION
-- ============================================================================

DO $$
DECLARE
    enum_count INTEGER;
    uuid_column_count INTEGER;
    table_exists BOOLEAN;
BEGIN
    -- Check enums
    SELECT COUNT(*) INTO enum_count FROM pg_type 
    WHERE typname IN ('chatstatusenum', 'message_role_enum');
    
    RAISE NOTICE 'Enums created: %', enum_count;
    
    -- Check UUID columns
    SELECT COUNT(*) INTO uuid_column_count FROM information_schema.columns 
    WHERE table_name IN ('chat', 'message', 'chat_group', 'user_state')
      AND column_name LIKE '%_id'
      AND udt_name = 'uuid';
    
    RAISE NOTICE 'UUID columns: %', uuid_column_count;
    
    -- Check message_metadata
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_name = 'message_metadata'
    ) INTO table_exists;
    
    RAISE NOTICE 'message_metadata exists: %', table_exists;
    
    IF enum_count >= 2 AND uuid_column_count >= 5 AND table_exists THEN
        RAISE NOTICE '✓ Migration completed successfully!';
    ELSE
        RAISE WARNING '⚠ Some migration steps may need manual intervention';
    END IF;
END$$;

-- ============================================================================
-- End of Migration Script
-- ============================================================================
