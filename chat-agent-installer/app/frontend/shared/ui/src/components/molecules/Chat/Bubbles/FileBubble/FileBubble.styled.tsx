import styled from 'styled-components';
import { Image } from 'antd';

export const StyledFileBubbleImage = styled(Image)`
  &.ant-image-img {
    width: 7rem !important;
    height: 7rem !important;
    border-radius: 0.5rem;
    object-fit: cover;
    & + .ant-image-mask {
      border-radius: 0.5rem !important;
    }
  }
`;
