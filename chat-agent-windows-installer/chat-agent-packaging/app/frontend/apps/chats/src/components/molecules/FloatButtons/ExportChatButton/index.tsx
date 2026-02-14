import { FC, useMemo, useState } from 'react';
import exportFromJSON from 'export-from-json';
import { IoMdCloudDownload } from 'react-icons/io';
import { App, FloatButton } from 'antd';

import { useAppSelector } from '@shared/ui/store';
import useHandleError from '@shared/ui/hooks/useHandleError.hook';
import customDayjs from '@shared/ui/libs/dayjs.libs';
import { getChat } from '@shared/ui/services/chats.services';

import { ExportChatButtonProps } from '@/components/molecules/FloatButtons/ExportChatButton/ExportChatButton.props';
import { RawMessageType } from '@shared/ui/types/messages.types';

const ExportChatButton: FC<ExportChatButtonProps> = (props) => {
  const { message } = App.useApp();
  const activeChat = useAppSelector((store) => store.chats.activeChat);
  const aiTyping = useAppSelector((store) => store.chats.aiTyping);
  const [loading, setLoading] = useState(false);
  const handleError = useHandleError();
  const disableButton = useMemo(
    () => !activeChat || loading || aiTyping,
    [activeChat, aiTyping, loading],
  );

  const handleClick = async () => {
    try {
      if (disableButton) return;
      setLoading(true);
      message.loading('The chat history exporting in progress...', 1);
      const { messages = {} } = await getChat({
        id: activeChat?.chat_id as string,
      });
      exportFromJSON({
        data: Object.entries(messages as RawMessageType).map(
          ([id, message]) => ({
            message_id: id,
            content: message?.content ?? '',
            role: message?.role ?? '',
            version_count: message?.version_count,
            version_index: message?.version_index,
            created_at: message?.created_at,
            attachments: message?.attachments,
          }),
        ),
        fileName: `Chat history "${activeChat?.title}" ${customDayjs().format('DD.MM.YYYY')}`,
        exportType: 'json',
      });
      message.success('The chat history has been exported successfully.');
    } catch (e) {
      handleError(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <FloatButton
      onClick={handleClick}
      icon={<IoMdCloudDownload />}
      {...props}
    />
  );
};

export default ExportChatButton;
