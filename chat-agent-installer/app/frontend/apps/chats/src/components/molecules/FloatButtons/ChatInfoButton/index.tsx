import { FC, useState } from 'react';
import { FloatButton } from 'antd';

import ChatInfoDrawer from '@/components/molecules/Drawers/ChatInfoDrawer';

import { ChatInfoButtonProps } from '@/components/molecules/FloatButtons/ChatInfoButton/ChatInfoButton.props';
import { InfoOutlined } from '@ant-design/icons';
import { useAppSelector } from '@shared/ui/store';

const ChatInfoButton: FC<ChatInfoButtonProps> = (props) => {
  const aiTyping = useAppSelector((store) => store.chats.aiTyping);
  const [open, setOpen] = useState(false);
  return (
    <>
      <FloatButton
        onClick={() => !aiTyping && setOpen(true)}
        icon={<InfoOutlined />}
        {...props}
      />
      <ChatInfoDrawer open={open} onClose={() => setOpen(false)} />
    </>
  );
};

export default ChatInfoButton;
