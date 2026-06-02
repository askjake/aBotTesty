import { Modal } from 'antd';
import styled from 'styled-components';

export const StyledSearchModal = styled(Modal)`
  &.ant-modal {
    min-width: 50vw;
    & .ant-modal-content {
      padding: 0;
    }
    & .ant-modal-header {
      margin-bottom: 0;
      padding: 15px;
      border-bottom: 1px solid ${({ theme }) => theme?.colors?.light || '#f3f4f6'};
    }
    & .ant-modal-title {
      width: 95%;
      overflow: hidden;
    }
    & .ant-conversations {
      padding: 0 0 0 15px;
    }

    & .empty-chats {
      height: 50vh;
    }
  }
`;
