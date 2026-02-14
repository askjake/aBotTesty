import { IoSettingsOutline } from 'react-icons/io5';
import { Tooltip } from 'antd';
import { FC } from 'react';

import ExportChatButton from '@/components/molecules/FloatButtons/ExportChatButton';
import { ChatSettingsStyled } from '@/components/organisms/ChatSettings/ChatSettings.styled';
import ChatInfoButton from '@/components/molecules/FloatButtons/ChatInfoButton';

import { ChatSettingsProps } from '@/components/organisms/ChatSettings/ChatSettings.props';

const ChatSettings: FC<ChatSettingsProps> = ({ ...props }) => {
  return (
    <ChatSettingsStyled
      shape='circle'
      trigger='click'
      icon={<IoSettingsOutline />}
      {...props}
    >
      <Tooltip title='Export chat history to the json file' placement='left'>
        <ExportChatButton />
      </Tooltip>
      <Tooltip title='Information about the current chat' placement='left'>
        <ChatInfoButton />
      </Tooltip>
    </ChatSettingsStyled>
  );
};

export default ChatSettings;
