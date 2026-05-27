import styled from 'styled-components';
import { Bubble } from '@ant-design/x';

export const StyledCustomBubble = styled(Bubble)`
  &.ant-bubble {
    & .ant-bubble-footer {
      margin-top: 0.5rem;
    }

    &[role='user'] {
      & .ant-bubble-body {
        max-width: 50%;
        & .ant-bubble-content {
          white-space: break-spaces;
        }
      }
    }

    &[role='assistant'] {
      & .ant-bubble-body {
        max-width: 75%;
      }
    }

    &[role='error'] {
      & .ant-bubble-content {
        padding: 0;
      }
    }

    &[role='assistant'],
    &[role='error'] {
      & .ant-avatar {
        background: ${({ theme }) => theme?.colors?.green || '#34d399'};
      }
    }

    & .ant-bubble-content {
      &:has(.ant-input) {
        width: 100%;
      }

      & p:last-child {
        margin-bottom: 0;
      }

      & details {
        /* Remove the transition that causes layout shifts */
        /* transition: height 0.2s ease-out; */

        &:not(:last-child) {
          margin-bottom: 1rem;
        }

        &[open] {
          & summary {
            list-style-type: none;
            &::after {
              transform: rotate(90deg);
            }
          }

          & .details-content {
            margin-top: 1rem;
            padding-left: 1rem;
            position: relative;

            &::before {
              content: '';
              display: block;
              height: 100%;
              width: 0.2rem;
              background-color: ${({ theme }) => theme?.colors?.primary || '#fc1c39'};
              position: absolute;
              left: 0;
              top: 0;
              bottom: 0;
              border-radius: 1rem;
            }
          }
        }

        & summary {
          list-style-type: none;
          display: flex;
          align-items: center;
          gap: 0.5rem;
          font-weight: bold;

          &::after {
            content: '';
            display: inline-block;
            width: 15px;
            height: 15px;
            background: center / 130% no-repeat url('/img/arrow.svg');
            /* Add smooth transition only to the arrow rotation */
            transition: transform 0.2s ease-out;
          }
        }

        &[data-spoiler-title='Thinking...'] summary::after {
          background: center / contain no-repeat url('/img/loader.svg');
        }
      }
    }
  }
` as typeof Bubble;
