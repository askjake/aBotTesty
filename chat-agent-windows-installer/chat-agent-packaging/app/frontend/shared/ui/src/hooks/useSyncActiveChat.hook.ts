import { useEffect, useRef } from 'react';
import { useAppSelector } from '@shared/ui/store';
import { activateChat } from '@shared/ui/services/chats.services';

/**
 * Hook to automatically sync active chat with backend
 * 
 * When the frontend sets an active chat in Redux, this hook
 * automatically calls the backend API to set the same chat as
 * active in the user's session state.
 * 
 * This enables backend features that depend on knowing which
 * chat is currently active (like journal generation, summaries, etc.)
 */
export const useSyncActiveChat = () => {
  const activeChat = useAppSelector((store) => store.chats.activeChat);
  const previousChatId = useRef<string | null>(null);

  useEffect(() => {
    const syncActiveChat = async () => {
      // Only sync if chat_id exists and has changed
      if (activeChat?.chat_id && activeChat.chat_id !== previousChatId.current) {
        try {
          await activateChat(activeChat.chat_id);
          console.debug(`Synced active chat: ${activeChat.chat_id}`);
          previousChatId.current = activeChat.chat_id;
        } catch (error) {
          console.error('Failed to sync active chat with backend:', error);
          // Don't throw - this is a non-critical sync operation
        }
      } else if (!activeChat?.chat_id && previousChatId.current) {
        // Chat was deactivated
        previousChatId.current = null;
      }
    };

    syncActiveChat();
  }, [activeChat?.chat_id]);
};
